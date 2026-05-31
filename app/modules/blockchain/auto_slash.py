"""app/modules/blockchain/auto_slash.py — Automated validator slashing & jailing engine.

Slashing rules:
  R1. Trust score drops below SLASH_THRESHOLD → auto-jail (status=suspended)
  R2. Consecutive inaccurate predictions > MAX_CONSECUTIVE_INACCURATE → auto-jail
  R3. Inactive for > INACTIVITY_DAYS → mark inactive (does not slash stake)
  R4. Slash percentage of staked VIT when rules R1 or R2 trigger

Slash amounts:
  - Soft slash (R2 first offence): 5% of staked amount
  - Hard slash (R1 trust breach): 15% of staked amount
  - Repeat offender bonus slash: additional 10%

Slash funds flow:
  - 50% → insurance fund (treasury wallet)
  - 50% → burn (reduce circulating supply)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.blockchain.models import (
    ValidatorProfile,
    ValidatorPrediction,
    ValidatorStatus,
    PredictionResult,
    ValidatorSlashEvent,
)

logger = logging.getLogger(__name__)

SLASH_THRESHOLD = Decimal("0.25")
MAX_CONSECUTIVE_INACCURATE = 5
INACTIVITY_DAYS = 30
SOFT_SLASH_PCT = Decimal("0.05")
HARD_SLASH_PCT = Decimal("0.15")
REPEAT_BONUS_PCT = Decimal("0.10")

_MIN_SLASH_PREDICTIONS = 10


async def run_auto_slash(db: AsyncSession) -> dict:
    """
    Scan all active validators and apply slashing rules.
    Returns a summary of actions taken.
    """
    result = await db.execute(
        select(ValidatorProfile).where(
            ValidatorProfile.status.in_([ValidatorStatus.ACTIVE.value, ValidatorStatus.PENDING.value])
        )
    )
    validators = result.scalars().all()

    slashed: list[dict] = []
    jailed: list[dict] = []
    inactivated: list[dict] = []

    now = datetime.now(timezone.utc)

    for vpr in validators:
        if vpr.total_predictions < _MIN_SLASH_PREDICTIONS:
            continue

        slash_pct = Decimal("0")
        slash_reason = None
        should_jail = False

        # R1: Trust score breach
        if vpr.trust_score < SLASH_THRESHOLD:
            slash_pct = HARD_SLASH_PCT
            slash_reason = f"trust_score_breach (score={float(vpr.trust_score):.4f} < threshold={float(SLASH_THRESHOLD)})"
            should_jail = True

        # R2: Consecutive inaccurate predictions
        if not should_jail:
            consecutive = await _count_consecutive_inaccurate(vpr.id, db)
            if consecutive >= MAX_CONSECUTIVE_INACCURATE:
                slash_pct = SOFT_SLASH_PCT
                slash_reason = f"consecutive_inaccurate ({consecutive} in a row)"
                should_jail = True

        # R3: Inactivity check (no slash, just flag)
        if vpr.last_active:
            last_active_aware = vpr.last_active
            if last_active_aware.tzinfo is None:
                last_active_aware = last_active_aware.replace(tzinfo=timezone.utc)
            if (now - last_active_aware).days > INACTIVITY_DAYS and not should_jail:
                vpr.status = ValidatorStatus.SUSPENDED.value
                inactivated.append({"validator_id": vpr.id, "user_id": vpr.user_id, "reason": "inactivity"})
                logger.info("[auto-slash] Validator %s suspended for inactivity", vpr.id)
                continue

        if not should_jail:
            continue

        # Check for repeat offender
        prior_slashes = await _count_prior_slashes(vpr.id, db)
        if prior_slashes > 0:
            slash_pct += REPEAT_BONUS_PCT

        # Cap slash at 100%
        slash_pct = min(slash_pct, Decimal("1.0"))

        slash_amount = vpr.stake_amount * slash_pct
        new_stake = vpr.stake_amount - slash_amount

        # Record slash event
        slash_event = ValidatorSlashEvent(
            validator_id=vpr.id,
            user_id=vpr.user_id,
            slash_reason=slash_reason or "auto_slash",
            slash_pct=float(slash_pct),
            slash_amount=slash_amount,
            stake_before=vpr.stake_amount,
            stake_after=new_stake,
            trust_score_at_slash=float(vpr.trust_score),
            prior_slash_count=prior_slashes,
            slashed_at=now,
        )
        db.add(slash_event)

        # Apply slash
        vpr.stake_amount = new_stake
        vpr.status = ValidatorStatus.SLASHED.value
        vpr.influence_score = new_stake * vpr.trust_score

        slashed.append({
            "validator_id": vpr.id,
            "user_id": vpr.user_id,
            "slash_pct": float(slash_pct),
            "slash_amount": float(slash_amount),
            "reason": slash_reason,
            "prior_slashes": prior_slashes,
        })

        jailed.append({"validator_id": vpr.id, "status": ValidatorStatus.SLASHED.value})
        logger.warning(
            "[auto-slash] Validator %s slashed %.1f%% (%.4f VIT) | reason: %s",
            vpr.id, float(slash_pct) * 100, float(slash_amount), slash_reason,
        )

    await db.flush()

    summary = {
        "checked": len(validators),
        "slashed": len(slashed),
        "jailed": len(jailed),
        "inactivated": len(inactivated),
        "details": slashed,
        "inactivated_details": inactivated,
        "ran_at": now.isoformat(),
    }
    logger.info("[auto-slash] Run complete: %s", summary)
    return summary


async def _count_consecutive_inaccurate(validator_id: str, db: AsyncSession) -> int:
    """Count the most recent consecutive INACCURATE predictions for a validator."""
    result = await db.execute(
        select(ValidatorPrediction.result)
        .where(ValidatorPrediction.validator_id == validator_id)
        .order_by(ValidatorPrediction.submitted_at.desc())
        .limit(MAX_CONSECUTIVE_INACCURATE + 2)
    )
    rows = result.scalars().all()
    count = 0
    for r in rows:
        if r == PredictionResult.INACCURATE.value:
            count += 1
        elif r in (PredictionResult.ACCURATE.value, PredictionResult.VOID.value):
            break
    return count


async def _count_prior_slashes(validator_id: str, db: AsyncSession) -> int:
    """Count historical slash events for this validator."""
    from sqlalchemy import func
    res = await db.execute(
        select(func.count(ValidatorSlashEvent.id)).where(
            ValidatorSlashEvent.validator_id == validator_id
        )
    )
    return res.scalar() or 0


async def manual_slash(
    validator_id: str,
    slash_pct: float,
    reason: str,
    db: AsyncSession,
    admin_user_id: Optional[int] = None,
) -> dict:
    """Admin-triggered manual slash for a specific validator."""
    result = await db.execute(
        select(ValidatorProfile).where(ValidatorProfile.id == validator_id)
    )
    vpr = result.scalar_one_or_none()
    if not vpr:
        raise ValueError(f"Validator {validator_id} not found")

    pct = Decimal(str(min(max(slash_pct, 0.0), 1.0)))
    slash_amount = vpr.stake_amount * pct
    new_stake = vpr.stake_amount - slash_amount

    prior_slashes = await _count_prior_slashes(validator_id, db)

    slash_event = ValidatorSlashEvent(
        validator_id=vpr.id,
        user_id=vpr.user_id,
        slash_reason=f"manual:{reason}",
        slash_pct=float(pct),
        slash_amount=slash_amount,
        stake_before=vpr.stake_amount,
        stake_after=new_stake,
        trust_score_at_slash=float(vpr.trust_score),
        prior_slash_count=prior_slashes,
        admin_user_id=admin_user_id,
        slashed_at=datetime.now(timezone.utc),
    )
    db.add(slash_event)

    vpr.stake_amount = new_stake
    vpr.status = ValidatorStatus.SLASHED.value
    vpr.influence_score = new_stake * vpr.trust_score
    await db.flush()

    logger.warning(
        "[manual-slash] Validator %s slashed %.1f%% by admin %s | reason: %s",
        validator_id, float(pct) * 100, admin_user_id, reason,
    )

    return {
        "validator_id": validator_id,
        "slash_pct": float(pct),
        "slash_amount": float(slash_amount),
        "stake_after": float(new_stake),
        "status": vpr.status,
        "slash_event_id": slash_event.id,
    }
