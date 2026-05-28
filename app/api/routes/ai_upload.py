"""AI Sources — real-time API-key-driven AI prediction ingestion & status panel."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, distinct, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import AIPrediction, Match
from app.api.deps import get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-upload", tags=["AI Sources"])

# ── Provider registry ─────────────────────────────────────────────────────────

def _get_provider_status() -> List[Dict]:
    """Check each AI provider's API key health without importing config at module level."""
    try:
        from app.config import (
            GEMINI_API_KEY, CLAUDE_API_KEY, OPENAI_API_KEY,
            DEEPSEEK_API_KEY,
        )
    except Exception:
        GEMINI_API_KEY = CLAUDE_API_KEY = OPENAI_API_KEY = DEEPSEEK_API_KEY = ""

    # Puter is always available (browser-side / free)
    providers = [
        {"id": "gemini",   "name": "Gemini (Google)",  "key": GEMINI_API_KEY,   "priority": 1},
        {"id": "claude",   "name": "Claude (Anthropic)","key": CLAUDE_API_KEY,   "priority": 2},
        {"id": "openai",   "name": "OpenAI / GPT-4",   "key": OPENAI_API_KEY,   "priority": 3},
        {"id": "deepseek", "name": "DeepSeek",          "key": DEEPSEEK_API_KEY, "priority": 4},
        {"id": "puter",    "name": "Puter AI",          "key": "puter_builtin",  "priority": 5},
    ]

    statuses = []
    for p in providers:
        key = p["key"] or ""
        if p["id"] == "puter":
            configured = True
            status_label = "available"
        elif len(key) >= 20:
            configured = True
            status_label = "configured"
        elif len(key) > 0:
            configured = False
            status_label = "key_too_short"
        else:
            configured = False
            status_label = "no_key"

        statuses.append({
            "id":       p["id"],
            "name":     p["name"],
            "priority": p["priority"],
            "configured": configured,
            "status":   status_label,
        })
    return statuses


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_provider_status(db: AsyncSession = Depends(get_db)):
    """Return live API provider status and prediction coverage stats."""
    providers = _get_provider_status()

    # Count auto-generated predictions per source
    counts_q = await db.execute(
        select(AIPrediction.source, func.count(AIPrediction.id))
        .group_by(AIPrediction.source)
    )
    source_counts = {row[0]: row[1] for row in counts_q.all()}

    # Most recent sync time
    latest_q = await db.execute(
        select(func.max(AIPrediction.timestamp))
    )
    latest_ts = latest_q.scalar()

    # Upcoming matches with no AI coverage
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    uncovered_q = await db.execute(
        select(func.count(Match.id))
        .where(Match.status == "upcoming", Match.kickoff_time >= now)
        .where(
            ~Match.id.in_(
                select(AIPrediction.match_id).distinct()
            )
        )
    )
    uncovered = uncovered_q.scalar() or 0

    for p in providers:
        p["prediction_count"] = source_counts.get(p["id"], 0)

    return {
        "providers":       providers,
        "last_sync":       latest_ts.isoformat() if latest_ts else None,
        "uncovered_matches": uncovered,
        "total_predictions": sum(source_counts.values()),
    }


@router.get("/sources")
async def list_sources(db: AsyncSession = Depends(get_db)):
    """Return active AI sources with prediction counts."""
    providers = _get_provider_status()
    configured = [p for p in providers if p["configured"]]

    extra_q = await db.execute(select(distinct(AIPrediction.source)))
    db_sources = [r for r in extra_q.scalars().all() if r]

    known_ids = {p["id"] for p in providers}
    extra_names = [s for s in db_sources if s not in known_ids]
    all_sources = [p["id"] for p in providers] + sorted(extra_names)

    return {
        "sources":    all_sources,
        "count":      len(all_sources),
        "configured": len(configured),
        "providers":  providers,
    }


@router.get("/list")
async def list_predictions(
    limit:  int = Query(100, ge=1, le=500),
    source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List auto-ingested AI predictions with match info."""
    q = (
        select(AIPrediction, Match.home_team, Match.away_team, Match.league, Match.sport)
        .join(Match, AIPrediction.match_id == Match.id, isouter=True)
        .order_by(AIPrediction.timestamp.desc())
        .limit(limit)
    )
    if source:
        q = q.where(AIPrediction.source == source.lower())

    rows = (await db.execute(q)).all()

    predictions = [
        {
            "id":         ai_pred.id,
            "match_id":   ai_pred.match_id,
            "match":      f"{home or '?'} vs {away or '?'}",
            "league":     league or "",
            "sport":      sport or "football",
            "source":     ai_pred.source,
            "home_prob":  round(ai_pred.home_prob, 4),
            "draw_prob":  round(ai_pred.draw_prob, 4),
            "away_prob":  round(ai_pred.away_prob, 4),
            "confidence": round(ai_pred.confidence or 0.7, 4),
            "reason":     ai_pred.reason,
            "created_at": ai_pred.timestamp.isoformat() if ai_pred.timestamp else None,
            "was_correct":   ai_pred.was_correct,
            "is_certified":  ai_pred.is_certified,
            "is_automated":  True,
        }
        for ai_pred, home, away, league, sport in rows
    ]
    return {"count": len(predictions), "predictions": predictions}


@router.post("/sync")
async def sync_ai_sources(
    background_tasks: BackgroundTasks,
    match_limit: int = Query(20, ge=1, le=50, description="Max upcoming matches to process"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    """
    Trigger automated AI prediction generation for upcoming matches.

    Uses the server-side AI cascade (Gemini → Claude → OpenAI → DeepSeek → Puter)
    to auto-generate AIPrediction records — no manual entry required.
    """
    # Delegate to the admin/ai-sources run-server logic
    try:
        from app.services.ai_ingestion import AIIngestionService
        from app.config import GEMINI_API_KEY, CLAUDE_API_KEY, OPENAI_API_KEY

        # Fetch upcoming matches without recent AI coverage
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        result = await db.execute(
            select(Match)
            .where(
                Match.status.in_(["upcoming", "scheduled"]),
                Match.kickoff_time >= now,
            )
            .order_by(Match.kickoff_time.asc())
            .limit(match_limit)
        )
        matches = result.scalars().all()

        if not matches:
            return {"status": "no_matches", "processed": 0, "message": "No upcoming matches found"}

        svc = AIIngestionService(db)
        results = []

        for match in matches:
            try:
                # Build analysis prompt for the AI
                prompt = (
                    f"Analyse this upcoming match and provide probability estimates:\n"
                    f"Match: {match.home_team} vs {match.away_team}\n"
                    f"League: {match.league}\n"
                    f"Sport: {match.sport or 'football'}\n"
                    f"Date: {match.kickoff_time.strftime('%Y-%m-%d') if match.kickoff_time else 'TBD'}\n\n"
                    f"Respond ONLY with a JSON object:\n"
                    f'{{"home_prob": 0.XX, "draw_prob": 0.XX, "away_prob": 0.XX, '
                    f'"confidence": 0.XX, "reason": "brief reasoning"}}'
                )

                # Use multi-provider AI client
                from app.services.ai_client import MultiProviderAIClient
                ai_client = MultiProviderAIClient()
                raw = await ai_client.complete(prompt, max_tokens=256)

                # Parse the JSON response
                import json, re
                json_match = re.search(r'\{[^{}]+\}', raw or "", re.DOTALL)
                if not json_match:
                    raise ValueError("No JSON in AI response")

                data = json.loads(json_match.group())
                hp = float(data.get("home_prob", 0.45))
                dp = float(data.get("draw_prob", 0.25))
                ap = float(data.get("away_prob", 0.30))
                cf = float(data.get("confidence", 0.70))
                reason = str(data.get("reason", ""))[:480]

                # Normalise
                total = hp + dp + ap
                if total > 0:
                    hp, dp, ap = hp / total, dp / total, ap / total

                ok = await svc.ingest_prediction(
                    match_id=match.id,
                    source="server",
                    home_prob=hp,
                    draw_prob=dp,
                    away_prob=ap,
                    confidence=cf,
                    reason=reason,
                    raw_content=raw[:2000] if raw else None,
                    submitted_by=current_user.id if current_user else None,
                )
                results.append({
                    "match_id": match.id,
                    "match":    f"{match.home_team} vs {match.away_team}",
                    "status":   "synced" if ok else "skipped",
                    "home_prob": round(hp, 3),
                    "away_prob": round(ap, 3),
                })

            except Exception as e:
                logger.warning("[ai-upload/sync] match_id=%s failed: %s", match.id, e)
                results.append({
                    "match_id": match.id,
                    "match":    f"{match.home_team} vs {match.away_team}",
                    "status":   "error",
                    "error":    str(e)[:120],
                })

        synced = sum(1 for r in results if r["status"] == "synced")
        return {
            "status":    "done",
            "processed": len(results),
            "synced":    synced,
            "results":   results,
        }

    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"AI client unavailable: {e}")
    except Exception as e:
        logger.error("[ai-upload/sync] unexpected error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-injuries")
async def sync_injury_news(
    leagues: Optional[List[str]] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger injury news fetch from Transfermarkt across all active leagues.
    Returns fresh injury data that is also stored for the match-detail injury tab.
    """
    try:
        from app.services.scraper import InjuryScraper, DEFAULT_SCRAPE_LEAGUES
        scraper = InjuryScraper()
        target = leagues or DEFAULT_SCRAPE_LEAGUES
        injuries = await scraper.fetch_all_injuries(leagues=target)
        return {
            "status":        "ok",
            "injuries_count": len(injuries),
            "leagues_scraped": target,
            "injuries":      injuries[:200],
        }
    except Exception as e:
        logger.error("[ai-upload/sync-injuries] %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
