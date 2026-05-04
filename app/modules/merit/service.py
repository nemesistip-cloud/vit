"""Merit Service — score calculation, tier management, decay, bonus VIT rewards."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.merit.models import (
    TIER_BONUS_PCT,
    TIER_THRESHOLDS,
    MeritEvent,
    MeritEventType,
    MeritScore,
    MeritTier,
)

logger = logging.getLogger(__name__)

POINTS_TABLE: dict[MeritEventType, Decimal] = {
    MeritEventType.PREDICTION_CORRECT:  Decimal("10"),
    MeritEventType.PREDICTION_INCORRECT: Decimal("-3"),
    MeritEventType.STREAK_BONUS:         Decimal("25"),
    MeritEventType.VALIDATOR_UPTIME:     Decimal("5"),
    MeritEventType.ORACLE_ACCURACY:      Decimal("8"),
    MeritEventType.GOVERNANCE_VOTE:      Decimal("3"),
    MeritEventType.GOVERNANCE_PROPOSAL:  Decimal("15"),
    MeritEventType.GRANT_RECIPIENT:      Decimal("50"),
    MeritEventType.REFERRAL_CONVERTED:   Decimal("20"),
    MeritEventType.STAKING_MILESTONE:    Decimal("30"),
    MeritEventType.SLASH_PENALTY:        Decimal("-50"),
    MeritEventType.INACTIVITY_DECAY:     Decimal("-5"),
    MeritEventType.TIER_PROMOTION:       Decimal("0"),
    MeritEventType.ADMIN_ADJUSTMENT:     Decimal("0"),
}

DECAY_THRESHOLD_DAYS = 7
DECAY_RATE_PER_DAY = Decimal("0.005")
MAX_DECAY_PCT = Decimal("0.20")


def _tier_for_score(score: Decimal) -> MeritTier:
    tier = MeritTier.UNRANKED
    for t, threshold in sorted(TIER_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
        if score >= threshold:
            tier = t
            break
    return tier


async def get_or_create_merit_score(db: AsyncSession, user_id: int) -> MeritScore:
    existing = await db.scalar(
        select(MeritScore).where(MeritScore.user_id == user_id)
    )
    if existing:
        return existing
    ms = MeritScore(user_id=user_id)
    db.add(ms)
    await db.commit()
    await db.refresh(ms)
    return ms


async def record_merit_event(
    db: AsyncSession,
    user_id: int,
    event_type: MeritEventType,
    points_override: Decimal | None = None,
    bonus_vit: Decimal = Decimal("0"),
    ref_id: str | None = None,
    description: str | None = None,
) -> MeritEvent:
    ms = await get_or_create_merit_score(db, user_id)

    points = points_override if points_override is not None else POINTS_TABLE[event_type]
    score_before = ms.score
    tier_before = ms.tier

    new_score = max(Decimal("0"), ms.score + points)
    new_tier = _tier_for_score(new_score)

    ms.score = new_score
    ms.tier = new_tier
    ms.last_activity_at = datetime.utcnow()

    if points > 0:
        ms.total_earned += points
    else:
        ms.total_lost += abs(points)

    if new_score > ms.peak_score:
        ms.peak_score = new_score
        ms.peak_tier = new_tier

    if bonus_vit > 0:
        ms.bonus_vit_earned += bonus_vit

    event = MeritEvent(
        merit_score_id=ms.id,
        user_id=user_id,
        event_type=event_type,
        points_delta=points,
        score_before=score_before,
        score_after=new_score,
        tier_before=tier_before,
        tier_after=new_tier,
        bonus_vit=bonus_vit,
        ref_id=ref_id,
        description=description,
    )
    db.add(event)

    if new_tier != tier_before:
        tier_event = MeritEvent(
            merit_score_id=ms.id,
            user_id=user_id,
            event_type=MeritEventType.TIER_PROMOTION,
            points_delta=Decimal("0"),
            score_before=new_score,
            score_after=new_score,
            tier_before=tier_before,
            tier_after=new_tier,
            description=f"Tier changed: {tier_before} → {new_tier}",
        )
        db.add(tier_event)

    await db.commit()
    await db.refresh(event)
    return event


async def apply_inactivity_decay(db: AsyncSession, user_id: int) -> MeritScore | None:
    ms = await db.scalar(select(MeritScore).where(MeritScore.user_id == user_id))
    if not ms or ms.score <= 0:
        return None

    now = datetime.utcnow()
    last = ms.last_activity_at or ms.created_at
    days_inactive = (now - last).days

    if days_inactive < DECAY_THRESHOLD_DAYS:
        return ms

    decay_days = days_inactive - DECAY_THRESHOLD_DAYS
    decay_pct = min(DECAY_RATE_PER_DAY * decay_days, MAX_DECAY_PCT)
    decay_points = (ms.score * decay_pct).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    if decay_points > 0:
        await record_merit_event(
            db, user_id,
            MeritEventType.INACTIVITY_DECAY,
            points_override=-decay_points,
            description=f"Inactivity decay: {days_inactive} days inactive",
        )
        ms.last_decay_at = now
        await db.commit()
        await db.refresh(ms)

    return ms


async def compute_merit_bonus_vit(
    db: AsyncSession,
    user_id: int,
    base_reward: Decimal,
) -> Decimal:
    ms = await db.scalar(select(MeritScore).where(MeritScore.user_id == user_id))
    if not ms:
        return Decimal("0")
    bonus_pct = TIER_BONUS_PCT.get(ms.tier, Decimal("0"))
    return (base_reward * bonus_pct).quantize(Decimal("0.000001"))


async def get_merit_leaderboard(db: AsyncSession, limit: int = 50) -> list[dict]:
    result = await db.execute(
        select(MeritScore).order_by(MeritScore.score.desc()).limit(limit)
    )
    rows = list(result.scalars().all())
    return [
        {
            "rank": i + 1,
            "user_id": r.user_id,
            "score": float(r.score),
            "tier": r.tier.value,
            "peak_score": float(r.peak_score),
            "bonus_vit_earned": float(r.bonus_vit_earned),
            "streak_days": r.streak_days,
        }
        for i, r in enumerate(rows)
    ]


async def get_tier_distribution(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(
        select(MeritScore.tier, func.count(MeritScore.id)).group_by(MeritScore.tier)
    )
    return {row[0].value: row[1] for row in result.all()}


async def get_user_merit_history(
    db: AsyncSession, user_id: int, limit: int = 50
) -> list[MeritEvent]:
    result = await db.execute(
        select(MeritEvent)
        .where(MeritEvent.user_id == user_id)
        .order_by(MeritEvent.occurred_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
