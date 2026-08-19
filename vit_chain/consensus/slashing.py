"""
vit_chain/consensus/slashing.py — Slashing enforcement for VIT Chain (Chain ID 7764).
Phase 1 gate: conditions enforced in CODE, not only in VALIDATOR_SYSTEM.md.

Conditions: DOUBLE_SIGN (10%), DOWNTIME (1%, after SLASHING_DOWNTIME_SLOTS misses),
            INVALID_BLOCK (5%). Appeal window: SLASHING_APPEAL_WINDOW_SLOTS slots.
"""
from __future__ import annotations
import logging
from decimal import Decimal
from enum import Enum
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_env, get_int_env
from app.core.errors import AppError
from app.services.cache import _get_redis

logger = logging.getLogger(__name__)

DOWNTIME_SLOT_THRESHOLD: int   = get_int_env("SLASHING_DOWNTIME_SLOTS", 50)
SLASH_APPEAL_WINDOW_SLOTS: int = get_int_env("SLASHING_APPEAL_WINDOW_SLOTS", 500)
SLASH_RATE_DOUBLE_SIGN   = Decimal("0.10")
SLASH_RATE_DOWNTIME      = Decimal("0.01")
SLASH_RATE_INVALID_BLOCK = Decimal("0.05")


class SlashReason(str, Enum):
    DOUBLE_SIGN   = "DOUBLE_SIGN"
    DOWNTIME      = "DOWNTIME"
    INVALID_BLOCK = "INVALID_BLOCK"


class SlashAppealStatus(str, Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SlashingManager:
    """
    Enforces slashing conditions on VIT Chain validators.

    Integration — add to ConsensusEngine.on_new_block():
        from vit_chain.consensus.slashing import slashing_manager, SlashReason
        await slashing_manager.check_and_slash(db, proposer, SlashReason.DOUBLE_SIGN, evidence)
    """

    async def check_and_slash(self, db: AsyncSession, validator_address: str,
                               reason: "SlashReason", evidence: Optional[str] = None,
                               current_slot: int = 0) -> Optional[dict]:
        try:
            from app.db.models import ValidatorStake, SlashEvent
            async with db.begin():
                res = await db.execute(select(ValidatorStake).where(
                    ValidatorStake.address == validator_address, ValidatorStake.active.is_(True)))
                row = res.scalar_one_or_none()
                if row is None:
                    logger.warning("[slashing] %s not found or inactive — skipping.", validator_address)
                    return None
                rate = {SlashReason.DOUBLE_SIGN: SLASH_RATE_DOUBLE_SIGN,
                        SlashReason.DOWNTIME: SLASH_RATE_DOWNTIME,
                        SlashReason.INVALID_BLOCK: SLASH_RATE_INVALID_BLOCK}[reason]
                slash_amount = int(Decimal(str(row.stake_amount)) * rate)
                if slash_amount <= 0:
                    return None
                new_stake = max(0, row.stake_amount - slash_amount)
                await db.execute(update(ValidatorStake).where(
                    ValidatorStake.address == validator_address
                ).values(stake_amount=new_stake, active=(new_stake > 0)))
                event = SlashEvent(
                    validator_address=validator_address, reason=reason.value,
                    slash_amount=slash_amount, stake_before=row.stake_amount,
                    stake_after=new_stake, evidence=evidence or "",
                    appeal_deadline_slot=current_slot + SLASH_APPEAL_WINDOW_SLOTS)
                db.add(event)
            logger.warning("[slashing] SLASHED %s | %s | -%d | %d→%d | appeal_slot=%d",
                           validator_address, reason.value, slash_amount,
                           row.stake_amount, new_stake, event.appeal_deadline_slot)
            return {"validator": validator_address, "reason": reason.value,
                    "slash_amount": slash_amount, "stake_before": row.stake_amount,
                    "stake_after": new_stake, "appeal_deadline_slot": event.appeal_deadline_slot}
        except AppError:
            raise
        except Exception as exc:
            raise AppError(code="SLASHING_FAILED", message=f"Slash failed for {validator_address}: {exc}") from exc

    async def check_downtime(self, db, validator_address, missed_slots, current_slot=0):
        if missed_slots < DOWNTIME_SLOT_THRESHOLD:
            return None
        return await self.check_and_slash(db, validator_address, SlashReason.DOWNTIME,
            evidence=f"Missed {missed_slots} consecutive slots (threshold={DOWNTIME_SLOT_THRESHOLD})",
            current_slot=current_slot)

    async def submit_appeal(self, db, slash_event_id, validator_address, justification):
        try:
            from app.db.models import SlashEvent, SlashAppeal
            async with db.begin():
                res = await db.execute(select(SlashEvent).where(
                    SlashEvent.id == slash_event_id, SlashEvent.validator_address == validator_address))
                if res.scalar_one_or_none() is None:
                    raise AppError(code="SLASH_EVENT_NOT_FOUND", message=f"Event {slash_event_id} not found.")
                db.add(SlashAppeal(slash_event_id=slash_event_id, validator_address=validator_address,
                                   justification=justification, status=SlashAppealStatus.PENDING.value))
            return {"slash_event_id": slash_event_id, "status": SlashAppealStatus.PENDING.value}
        except AppError:
            raise
        except Exception as exc:
            raise AppError(code="APPEAL_FAILED", message=str(exc)) from exc


slashing_manager = SlashingManager()


class SlashEngine:
    """Compatibility adapter for the storage consensus engine.

    The slashing implementation was moved to ``SlashingManager`` when
    validator stake and appeal records were added.  The storage consensus
    engine still uses the older ``record_participation`` and
    ``check_absent_nodes`` interface, so keep that interface as a thin adapter
    instead of breaking consensus startup.
    """

    def __init__(self) -> None:
        self.manager = slashing_manager

    async def record_participation(self, validator_address: str) -> None:
        """Reset the missed-slot counter after a validator participates."""
        redis = _get_redis()
        if redis is None:
            return
        try:
            await redis.set(f"vit:node:misses:{validator_address}", 0)
        except Exception as exc:
            logger.warning(
                "[slashing] could not reset participation counter for %s: %s",
                validator_address,
                exc,
            )

    async def check_absent_nodes(
        self,
        db: AsyncSession,
        absent_nodes: list[str],
        current_slot: int = 0,
    ) -> None:
        """Track missed slots and slash validators after the configured threshold."""
        redis = _get_redis()
        for validator_address in absent_nodes:
            missed_slots = 1
            if redis is not None:
                try:
                    missed_slots = int(
                        await redis.incr(f"vit:node:misses:{validator_address}")
                    )
                except Exception as exc:
                    logger.warning(
                        "[slashing] could not track missed slot for %s: %s",
                        validator_address,
                        exc,
                    )

            if missed_slots >= DOWNTIME_SLOT_THRESHOLD:
                await self.manager.check_downtime(
                    db,
                    validator_address,
                    missed_slots,
                    current_slot=current_slot,
                )
