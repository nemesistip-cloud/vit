"""Admin/Analyst AI Sources panel — upload raw Claude/Grok/etc analysis per match."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import AIPrediction, Match, User
from app.services.ai_ingestion import AIIngestionService
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/ai-sources", tags=["admin-ai-sources"])


ALLOWED_SOURCES = {
    "chatgpt", "gemini", "claude", "grok",
    "deepseek", "perplexity", "mistral", "manual",
}
ALLOWED_TIERS = {"analyst", "pro", "elite"}


def _can_upload(user: User) -> bool:
    if getattr(user, "role", None) == "admin":
        return True
    tier = (getattr(user, "subscription_tier", "") or "").lower()
    return tier in ALLOWED_TIERS


async def require_uploader(current_user: User = Depends(get_current_user)) -> User:
    if not _can_upload(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI source uploads require an admin account or analyst+ subscription tier",
        )
    return current_user


class AISourceIngestPayload(BaseModel):
    match_id: int = Field(..., gt=0)
    source: str = Field(..., min_length=2, max_length=50)
    home_prob: float = Field(..., ge=0.0, le=1.0)
    draw_prob: float = Field(..., ge=0.0, le=1.0)
    away_prob: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(0.7, ge=0.0, le=1.0)
    reason: Optional[str] = Field(None, max_length=500)
    raw_content: Optional[str] = Field(None, max_length=20000)

    @validator("source")
    def _src(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ALLOWED_SOURCES:
            raise ValueError(
                f"Source must be one of: {sorted(ALLOWED_SOURCES)}"
            )
        return v

    @validator("away_prob")
    def _sum_check(cls, v, values):
        h = values.get("home_prob", 0.0)
        d = values.get("draw_prob", 0.0)
        total = (h or 0) + (d or 0) + (v or 0)
        if total <= 0:
            raise ValueError("Probabilities must sum to a positive value")
        # Tolerate up to 10% off — service will normalise
        if abs(total - 1.0) > 0.1:
            raise ValueError(
                f"home + draw + away probabilities should be close to 1.0 (got {total:.3f})"
            )
        return v


@router.get("/permissions")
async def my_permissions(current_user: User = Depends(get_current_user)):
    """Tell the frontend whether the current user can upload AI sources."""
    return {
        "can_upload": _can_upload(current_user),
        "role": getattr(current_user, "role", "user"),
        "tier": getattr(current_user, "subscription_tier", "viewer"),
        "allowed_sources": sorted(ALLOWED_SOURCES),
    }


@router.get("/matches")
async def list_matches_for_ingest(
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_uploader),
):
    """List upcoming/recent matches with current AI source coverage."""
    now = datetime.now(timezone.utc)
    res = await db.execute(
        select(Match)
        .where(Match.status.in_(["scheduled", "upcoming", "in_progress"]))
        .order_by(Match.match_date.asc())
        .limit(max(1, min(limit, 100)))
    )
    matches = res.scalars().all()
    if not matches:
        # fallback: most recent matches regardless of status
        res = await db.execute(
            select(Match).order_by(desc(Match.match_date)).limit(limit)
        )
        matches = res.scalars().all()

    match_ids = [m.id for m in matches]
    coverage: dict[int, list[str]] = {mid: [] for mid in match_ids}
    if match_ids:
        cov_res = await db.execute(
            select(AIPrediction.match_id, AIPrediction.source).where(
                AIPrediction.match_id.in_(match_ids)
            )
        )
        for mid, src in cov_res.all():
            coverage.setdefault(mid, []).append(src)

    return {
        "matches": [
            {
                "id": m.id,
                "home_team": m.home_team,
                "away_team": m.away_team,
                "league": m.league,
                "match_date": m.match_date.isoformat() if m.match_date else None,
                "status": m.status,
                "sources": sorted(set(coverage.get(m.id, []))),
            }
            for m in matches
        ]
    }


@router.get("/match/{match_id}")
async def list_sources_for_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_uploader),
):
    """All uploaded AI sources for a single match."""
    match_row = await db.execute(select(Match).where(Match.id == match_id))
    match = match_row.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    rows = await db.execute(
        select(AIPrediction)
        .where(AIPrediction.match_id == match_id)
        .order_by(desc(AIPrediction.timestamp))
    )
    preds = rows.scalars().all()

    return {
        "match": {
            "id": match.id,
            "home_team": match.home_team,
            "away_team": match.away_team,
            "league": match.league,
            "match_date": match.match_date.isoformat() if match.match_date else None,
            "status": match.status,
        },
        "predictions": [
            {
                "id": p.id,
                "source": p.source,
                "home_prob": p.home_prob,
                "draw_prob": p.draw_prob,
                "away_prob": p.away_prob,
                "confidence": p.confidence,
                "reason": p.reason,
                "raw_content": p.raw_content,
                "submitted_by": p.submitted_by,
                "is_certified": bool(p.is_certified),
                "was_correct": p.was_correct,
                "timestamp": p.timestamp.isoformat() if p.timestamp else None,
            }
            for p in preds
        ],
    }


@router.post("/ingest")
async def ingest_source(
    payload: AISourceIngestPayload,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_uploader),
):
    """Upload (or update) a single match's AI analysis from Claude/Grok/etc."""
    match_row = await db.execute(select(Match).where(Match.id == payload.match_id))
    match = match_row.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    service = AIIngestionService(db)
    ok = await service.ingest_prediction(
        match_id=payload.match_id,
        source=payload.source,
        home_prob=payload.home_prob,
        draw_prob=payload.draw_prob,
        away_prob=payload.away_prob,
        confidence=payload.confidence,
        reason=payload.reason,
        raw_content=payload.raw_content,
        submitted_by=user.id,
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to ingest AI source")

    logger.info(
        "AI source uploaded: match=%s source=%s by user=%s",
        payload.match_id, payload.source, user.id,
    )
    return {"status": "success", "match_id": payload.match_id, "source": payload.source}


@router.delete("/{prediction_id}")
async def delete_source(
    prediction_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_uploader),
):
    """Delete an uploaded AI source. Admins can delete any; analysts only their own."""
    row = await db.execute(select(AIPrediction).where(AIPrediction.id == prediction_id))
    pred = row.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail="AI prediction not found")

    is_admin = getattr(user, "role", None) == "admin"
    if not is_admin and pred.submitted_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete AI sources you uploaded",
        )

    await db.delete(pred)
    await db.commit()
    return {"status": "deleted", "id": prediction_id}
