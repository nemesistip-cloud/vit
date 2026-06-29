"""Validator Rewards — Track 7.2

Handles fixed reward distribution for validators aligned with oracle consensus.
"""

import logging
from decimal import Decimal
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.blockchain.models import ValidatorProfile, ValidatorPrediction, PredictionResult
from app.modules.wallet.models import PlatformConfig, Wallet, Currency, TransactionType
from app.modules.wallet.services import WalletService
from app.services.audit import write_audit

logger = logging.getLogger(__name__)


class ValidatorRewardDistributor:
    """Distributes fixed VIT rewards to validators following oracle consensus."""

    REWARD_KEY = "validator_reward_per_settlement"
    DEFAULT_REWARD = Decimal("5.0")

    @classmethod
    async def distribute(cls, db: AsyncSession,
                          match_id: str,
                          outcome: str,
                          consensus_validators: List[str]) -> dict:
        """
        Credits fixed rewards to validators who aligned with the consensus outcome.

        Args:
            db: Async database session.
            match_id: ID of the match being settled.
            outcome: Confirmed match outcome.
            consensus_validators: List of validator IDs who voted for the outcome.
        """
        # Load reward amount from PlatformConfig
        reward_res = await db.execute(
            select(PlatformConfig).where(PlatformConfig.key == cls.REWARD_KEY)
        )
        row = reward_res.scalar_one_or_none()
        reward_amount = Decimal(str(row.value)) if row and row.value else cls.DEFAULT_REWARD

        rewarded_count = 0
        total_distributed = Decimal("0")

        ws = WalletService(db)

        # Financial mutations inside a transaction block
        async with db.begin_nested():
            for val_id in consensus_validators:
                try:
                    # Get validator profile and wallet
                    val_res = await db.execute(
                        select(ValidatorProfile).where(ValidatorProfile.id == val_id)
                    )
                    val_profile = val_res.scalar_one_or_none()
                    if not val_profile:
                        continue

                    w_res = await db.execute(
                        select(Wallet).where(Wallet.user_id == val_profile.user_id)
                    )
                    wallet = w_res.scalar_one_or_none()
                    if not wallet:
                        continue

                    # Credit reward
                    await ws.credit(
                        wallet_id=wallet.id,
                        user_id=val_profile.user_id,
                        currency=Currency.VITCOIN,
                        amount=reward_amount,
                        tx_type=TransactionType.REWARD.value,
                        reference=f"val_reward:{match_id}:{val_id}",
                        metadata={"match_id": match_id, "type": "consensus_bonus"}
                    )

                    # Audit log per reward
                    await write_audit(
                        db=db,
                        admin_id=0,  # System automated
                        action="validator.reward",
                        target_type="validator",
                        target_id=val_id,
                        after={"reward": float(reward_amount), "match_id": match_id}
                    )

                    rewarded_count += 1
                    total_distributed += reward_amount

                except Exception as e:
                    logger.error(f"Failed to reward validator {val_id} for match {match_id}: {e}")

        return {
            "rewarded_count": rewarded_count,
            "total_vit_distributed": float(total_distributed)
        }
