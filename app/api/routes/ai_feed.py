# app/api/routes/ai_feed.py
"""API endpoints for live AI feed"""

import logging
from fastapi import APIRouter, Depends
from app.api.deps import get_optional_user
from app.schemas.schemas import MatchRequest
from app.services.live_ai_feed import LiveAIFeedService, AISource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-feed", tags=["AI Feed"])

ai_feed_service = LiveAIFeedService()


@router.post("/predictions")
async def get_ai_predictions(match: MatchRequest, current_user=Depends(get_optional_user)):
    """Get live AI predictions from all available free sources."""
    match_data = {
        "match_id": f"{match.home_team}_vs_{match.away_team}",
        "home_team": match.home_team,
        "away_team": match.away_team,
        "league": match.league,
        "market_odds": match.market_odds,
    }
    result = await ai_feed_service.get_live_predictions(match_data)
    return {
        "match": {
            "home_team": match.home_team,
            "away_team": match.away_team,
            "league": match.league,
        },
        "ai_predictions": result,
    }


@router.post("/consensus")
async def get_ai_consensus(match: MatchRequest, current_user=Depends(get_optional_user)):
    """Get AI consensus and compare with market odds."""
    match_data = {
        "match_id": f"{match.home_team}_vs_{match.away_team}",
        "home_team": match.home_team,
        "away_team": match.away_team,
        "league": match.league,
        "market_odds": match.market_odds,
    }
    result = await ai_feed_service.get_live_odds_and_predictions(match_data)

    opportunities = []
    if result.get("high_disagreement"):
        opportunities.append("High AI disagreement - information asymmetry detected")

    market_comparison = result.get("market_comparison", {})
    edges = market_comparison.get("edge_vs_market", {})
    for outcome, edge in edges.items():
        if edge > 0.03:
            opportunities.append(f"AI consensus shows +{edge*100:.1f}% edge on {outcome}")
        elif edge < -0.03:
            opportunities.append(f"Market is more confident on {outcome} than AI")

    result["opportunities"] = opportunities
    return result


@router.get("/sources")
async def get_available_sources():
    """Get list of available AI prediction sources and their status."""
    sources = []
    for source in ai_feed_service.sources:
        sources.append({
            "name": source["name"].value,
            "enabled": source["enabled"],
            "requires_api_key": source["name"] in [AISource.BZZOIRO, AISource.SPORTBOT],
        })

    return {
        "sources": sources,
        "total_enabled": sum(1 for s in sources if s["enabled"]),
        "instructions": {
            "sports_skills": "pip install sports-skills",
            "bzzoiro": "Sign up at sports.bzzoiro.com for free API key",
            "sportbot": "Sign up at sportbot.ai for free tier API key",
            "football_bin": "No setup required",
        },
    }


@router.get("/health")
async def ai_feed_health():
    """Check health of all AI feed sources."""
    health_status = {}
    for source in ai_feed_service.sources:
        health_status[source["name"].value] = {
            "enabled": source["enabled"],
            "status": "ready" if source["enabled"] else "disabled",
        }
    return health_status


@router.get("/matches")
async def get_ai_feed_matches(
    limit: int = 10,
    current_user=Depends(get_optional_user),
):
    """Return upcoming matches available for AI feed analysis."""
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import select, text
    from app.db.models import Match
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    lookahead = now + timedelta(days=7)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Match)
            .where(Match.actual_outcome.is_(None))
            .where(Match.kickoff_time >= now - timedelta(hours=6))
            .where(Match.kickoff_time <= lookahead)
            .order_by(Match.kickoff_time.asc())
            .limit(limit)
        )
        matches = result.scalars().all()

    return {
        "matches": [
            {
                "id": m.id,
                "home_team": m.home_team,
                "away_team": m.away_team,
                "league": m.league,
                "kickoff_time": m.kickoff_time.isoformat() if m.kickoff_time else None,
            }
            for m in matches
        ],
        "total": len(matches),
    }


@router.get("/recent")
async def get_ai_feed_recent(
    limit: int = 20,
    current_user=Depends(get_optional_user),
):
    """Return recent AI feed predictions across all sources."""
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.db.models import Match, Prediction
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    lookback = now - timedelta(days=3)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Match, Prediction)
            .join(Prediction, Match.id == Prediction.match_id)
            .where(Prediction.user_id.is_(None))
            .order_by(Prediction.timestamp.desc() if hasattr(Prediction, "timestamp") else Match.kickoff_time.desc())
            .limit(limit)
        )
        rows = result.all()

    return {
        "predictions": [
            {
                "match": f"{m.home_team} vs {m.away_team}",
                "league": m.league,
                "home_prob": round(float(p.home_prob or 0), 3) if p.home_prob else None,
                "draw_prob": round(float(p.draw_prob or 0), 3) if p.draw_prob else None,
                "away_prob": round(float(p.away_prob or 0), 3) if p.away_prob else None,
                "confidence": round(float(p.confidence or 0), 3) if p.confidence else None,
                "bet_side": p.bet_side,
                "source": "scie",
            }
            for m, p in rows
        ],
        "total": len(rows),
    }
