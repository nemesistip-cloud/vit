"""AI Upload — manual external AI prediction submission & listing."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, distinct, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import AIPrediction, Match
from app.api.deps import get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-upload", tags=["AI Upload"])

KNOWN_SOURCES: List[str] = [
    "chatgpt", "claude", "gemini", "grok", "deepseek",
    "perplexity", "copilot", "llama", "mistral", "qwen", "other",
]


class SubmitRequest(BaseModel):
    match_id: int = Field(..., gt=0)
    source: str = Field(..., min_length=1, max_length=50)
    home_prob: float = Field(..., ge=0.0, le=1.0)
    draw_prob: float = Field(..., ge=0.0, le=1.0)
    away_prob: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(0.7, ge=0.0, le=1.0)
    reason: Optional[str] = Field(None, max_length=500)
    raw_content: Optional[str] = None


@router.get("/sources")
async def list_sources(db: AsyncSession = Depends(get_db)):
    """Return known AI sources plus any previously used sources from the DB."""
    extra_q = await db.execute(select(distinct(AIPrediction.source)))
    db_sources = [r for r in extra_q.scalars().all() if r and r not in KNOWN_SOURCES]
    all_sources = KNOWN_SOURCES + sorted(db_sources)
    return {"sources": all_sources, "count": len(all_sources)}


@router.get("/list")
async def list_uploads(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List recent manually uploaded AI predictions with match names."""
    q = await db.execute(
        select(AIPrediction, Match.home_team, Match.away_team)
        .join(Match, AIPrediction.match_id == Match.id, isouter=True)
        .order_by(AIPrediction.timestamp.desc())
        .limit(limit)
    )
    rows = q.all()
    uploads = [
        {
            "id": ai_pred.id,
            "match_id": ai_pred.match_id,
            "match": f"{home or '?'} vs {away or '?'}",
            "source": ai_pred.source,
            "home_prob": round(ai_pred.home_prob, 4),
            "draw_prob": round(ai_pred.draw_prob, 4),
            "away_prob": round(ai_pred.away_prob, 4),
            "confidence": round(ai_pred.confidence or 0.7, 4),
            "created_at": ai_pred.timestamp.isoformat() if ai_pred.timestamp else None,
            "was_correct": ai_pred.was_correct,
            "is_certified": ai_pred.is_certified,
        }
        for ai_pred, home, away in rows
    ]
    return {"count": len(uploads), "uploads": uploads}


@router.post("/submit")
async def submit_upload(
    body: SubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    """Submit a manual AI prediction probability estimate."""
    total = body.home_prob + body.draw_prob + body.away_prob
    if total <= 0:
        raise HTTPException(status_code=422, detail="Probabilities must sum to > 0")

    hp = body.home_prob / total
    dp = body.draw_prob / total
    ap = body.away_prob / total

    match_q = await db.execute(select(Match).where(Match.id == body.match_id))
    if not match_q.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Match {body.match_id} not found")

    rec = AIPrediction(
        match_id=body.match_id,
        source=body.source.lower().strip(),
        home_prob=round(hp, 6),
        draw_prob=round(dp, 6),
        away_prob=round(ap, 6),
        confidence=body.confidence,
        reason=body.reason,
        raw_content=body.raw_content,
        submitted_by=current_user.id if current_user else None,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)

    logger.info(f"[ai-upload] submitted: match={rec.match_id} source={rec.source} "
                f"probs={rec.home_prob:.3f}/{rec.draw_prob:.3f}/{rec.away_prob:.3f}")

    return {
        "id": rec.id,
        "match_id": rec.match_id,
        "source": rec.source,
        "home_prob": round(rec.home_prob, 4),
        "draw_prob": round(rec.draw_prob, 4),
        "away_prob": round(rec.away_prob, 4),
        "submitted": True,
    }
