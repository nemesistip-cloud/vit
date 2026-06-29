"""Validator Slash Engine — Track 7.2

Monitors validator accuracy and slashes stakes for significant deviations
from the confirmed oracle consensus.
"""

import json
import logging
from decimal import Decimal
from typing import List, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.blockchain.models import (
    ValidatorProfile, ValidatorPrediction, ValidatorSlashEvent, ValidatorStatus
)
from app.modules.wallet.models import Wallet, Currency, TransactionType
from app.modules.wallet.services import WalletService
from app.services.audit import write_audit
from app.services.cache import _get_redis

logger = logging.getLogger(__name__)


class ValidatorSlashEngine:
    """Evaluates and executes slashing for deviating validators."""

    SLASH_THRESHOLD_PCT = Decimal("0.1")  # 10% of total stake
    DEVIATION_THRESHOLD = Decimal("0.3")  # >30% probability deviation from outcome

    @classmethod
    async def evaluate_slash(cls, db: AsyncSession,
                              match_id: str,
                              consensus_outcome: str,
                              all_submissions: List[Dict]) -> List[str]:
        """
        Scans validator submissions for a match and slashes those who deviated significantly.

        Args:
            db: Async database session.
            match_id: ID of the match.
            consensus_outcome: The confirmed outcome (home, draw, or away).
            all_submissions: List of submission dicts containing validator_id and p_{outcome}.
        """
        slashed_ids = []
        ws = WalletService(db)

        # Outcome field mapping
        outcome_field = f"p_{consensus_outcome}"

        async with db.begin_nested():
            for sub in all_submissions:
                val_id = sub.get("validator_id")
                # Probability assigned by validator to the ACTUAL outcome
                prob_assigned = Decimal(str(sub.get(outcome_field, 0)))

                # If deviation is too high (i.e., they assigned < 30% to the correct outcome)
                # Note: The spec says "deviation > 30%", which often implies |predicted - actual|.
                # In 1/0 outcome space, if they predicted 0.2 for home and home won, deviation is 0.8.
                # Threshold 0.3 suggests if their correct-side probability is < 0.7?
                # Actually, "deviation > 30% from consensus" usually means if consensus was 1.0 on 'home',
                # and they were < 0.7 on 'home', they deviate by > 0.3.

                if (Decimal("1.0") - prob_assigned) > cls.DEVIATION_THRESHOLD:
                    # Execute slash
                    success = await cls._execute_slash(db, val_id, match_id, ws)
                    if success:
                        slashed_ids.append(val_id)

        return slashed_ids

    @classmethod
    async def _execute_slash(cls, db: AsyncSession, val_id: str, match_id: str, ws: WalletService) -> bool:
        """Performs the stake reduction and records the event."""
        try:
            val_res = await db.execute(
                select(ValidatorProfile).where(ValidatorProfile.id == val_id)
            )
            val = val_res.scalar_one_or_none()
            if not val or val.status == ValidatorStatus.SLASHED.value:
                return False

            w_res = await db.execute(
                select(Wallet).where(Wallet.user_id == val.user_id)
            )
            wallet = w_res.scalar_one_or_none()
            if not wallet:
                return False

            stake_before = val.stake_amount
            slash_amount = stake_before * cls.SLASH_THRESHOLD_PCT
            stake_after = stake_before - slash_amount

            # Update validator stake
            val.stake_amount = stake_after
            if stake_after < Decimal("100"): # Minimum stake threshold
                 val.status = ValidatorStatus.SUSPENDED.value

            # Debit wallet
            await ws.debit(
                wallet_id=wallet.id,
                user_id=val.user_id,
                currency=Currency.VITCOIN,
                amount=slash_amount,
                tx_type=TransactionType.SLASH.value,
                reference=f"slash:{match_id}:{val_id}",
                metadata={"match_id": match_id, "reason": "consensus_deviation"}
            )

            # Record slash event
            slash_event = ValidatorSlashEvent(
                validator_id=val_id,
                user_id=val.user_id,
                slash_reason=f"Deviation from consensus on match {match_id}",
                slash_pct=cls.SLASH_THRESHOLD_PCT,
                slash_amount=slash_amount,
                stake_before=stake_before,
                stake_after=stake_after,
                trust_score_at_slash=val.trust_score,
            )
            db.add(slash_event)

            # Audit log
            await write_audit(
                db=db,
                admin_id=0,
                action="validator.slash",
                target_type="validator",
                target_id=val_id,
                after={"slash_amount": float(slash_amount), "match_id": match_id}
            )

            # Publish Redis event
            await cls._publish_slash_event(val_id, match_id, float(slash_amount))

            return True

        except Exception as e:
            logger.error(f"Failed to execute slash for validator {val_id}: {e}")
            return False

    @staticmethod
    async def _publish_slash_event(val_id: str, match_id: str, amount: float):
        """Publishes slash notification to Redis."""
        try:
            r = _get_redis()
            if r:
                payload = {
                    "event": "validator_slashed",
                    "validator_id": val_id,
                    "match_id": match_id,
                    "amount": amount
                }
                await r.publish(f"vit:validator:slashed_{val_id}", json.dumps(payload))
        except Exception as e:
            logger.error(f"Redis publish failed for slash {val_id}: {e}")
