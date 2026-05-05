"""Merit Routes — scores, events, tiers, leaderboard, decay."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.merit.models import MeritEventType, MeritTier, TIER_THRESHOLDS, TIER_BONUS_PCT
from app.modules.merit.service import (
    apply_inactivity_decay,
    compute_merit_bonus_vit,
    get_merit_leaderboard,
    get_or_create_merit_score,
    get_tier_distribution,
    get_user_merit_history,
    record_merit_event,
)

router = APIRouter(prefix="/api/merit", tags=["merit"])


class MeritEventRequest(BaseModel):
    user_id: int
    event_type: MeritEventType
    points_override: Optional[float] = None
    bonus_vit: float = 0.0
    ref_id: Optional[str] = None
    description: Optional[str] = None


class BonusCalcRequest(BaseModel):
    user_id: int
    base_reward: float


@router.get("/tiers")
async def get_tier_info():
    return {
        "tiers": [
            {
                "tier": tier.value,
                "min_score": threshold,
                "bonus_pct": float(TIER_BONUS_PCT.get(tier, Decimal("0")) * 100),
            }
            for tier, threshold in sorted(TIER_THRESHOLDS.items(), key=lambda x: x[1])
        ]
    }


@router.get("/leaderboard")
async def leaderboard(limit: int = 50, db: AsyncSession = Depends(get_db)):
    entries = await get_merit_leaderboard(db, limit=limit)
    return {"leaderboard": entries, "total": len(entries)}


@router.get("/distribution")
async def tier_distribution(db: AsyncSession = Depends(get_db)):
    dist = await get_tier_distribution(db)
    return {"distribution": dist}


@router.get("/users/{user_id}")
async def get_user_merit(user_id: int, db: AsyncSession = Depends(get_db)):
    ms = await get_or_create_merit_score(db, user_id)
    bonus_pct = TIER_BONUS_PCT.get(ms.tier, Decimal("0"))
    next_tier_score = None
    for tier, threshold in sorted(TIER_THRESHOLDS.items(), key=lambda x: x[1]):
        if threshold > float(ms.score):
            next_tier_score = threshold
            next_tier = tier.value
            break
    else:
        next_tier = None

    return {
        "user_id": ms.user_id,
        "score": float(ms.score),
        "tier": ms.tier.value,
        "peak_score": float(ms.peak_score),
        "peak_tier": ms.peak_tier.value,
        "total_earned": float(ms.total_earned),
        "total_lost": float(ms.total_lost),
        "streak_days": ms.streak_days,
        "bonus_vit_earned": float(ms.bonus_vit_earned),
        "current_bonus_pct": float(bonus_pct * 100),
        "next_tier": next_tier,
        "points_to_next_tier": (next_tier_score - float(ms.score)) if next_tier_score else 0,
        "last_activity_at": ms.last_activity_at.isoformat() if ms.last_activity_at else None,
        "updated_at": ms.updated_at.isoformat(),
    }


@router.get("/users/{user_id}/history")
async def get_history(user_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)):
    events = await get_user_merit_history(db, user_id, limit=limit)
    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type.value,
                "points_delta": float(e.points_delta),
                "score_before": float(e.score_before),
                "score_after": float(e.score_after),
                "tier_before": e.tier_before.value,
                "tier_after": e.tier_after.value,
                "bonus_vit": float(e.bonus_vit),
                "ref_id": e.ref_id,
                "description": e.description,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ]
    }


@router.post("/events")
async def record_event(req: MeritEventRequest, db: AsyncSession = Depends(get_db)):
    event = await record_merit_event(
        db,
        user_id=req.user_id,
        event_type=req.event_type,
        points_override=Decimal(str(req.points_override)) if req.points_override is not None else None,
        bonus_vit=Decimal(str(req.bonus_vit)),
        ref_id=req.ref_id,
        description=req.description,
    )
    return {
        "event_id": event.id,
        "points_delta": float(event.points_delta),
        "score_before": float(event.score_before),
        "score_after": float(event.score_after),
        "tier_before": event.tier_before.value,
        "tier_after": event.tier_after.value,
        "tier_changed": event.tier_before != event.tier_after,
    }


@router.post("/users/{user_id}/decay")
async def trigger_decay(user_id: int, db: AsyncSession = Depends(get_db)):
    ms = await apply_inactivity_decay(db, user_id)
    if not ms:
        raise HTTPException(status_code=404, detail="Merit score not found")
    return {"user_id": user_id, "score": float(ms.score), "tier": ms.tier.value, "last_decay_at": ms.last_decay_at.isoformat() if ms.last_decay_at else None}


@router.post("/bonus-calc")
async def calculate_bonus(req: BonusCalcRequest, db: AsyncSession = Depends(get_db)):
    bonus = await compute_merit_bonus_vit(db, req.user_id, Decimal(str(req.base_reward)))
    return {"user_id": req.user_id, "base_reward": req.base_reward, "bonus_vit": float(bonus)}
