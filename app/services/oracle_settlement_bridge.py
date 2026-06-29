"""Oracle Settlement Bridge — Track 7.1

Centralizes oracle consensus logic and triggers settlement events.
Ensures the 67% threshold is met before finalizing match results.
"""

import json
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.blockchain.models import OracleResult, ConsensusPrediction, ConsensusStatus, ValidatorPrediction
from app.modules.blockchain.settlement import settle_match as core_settle_match
from app.modules.blockchain.validator_rewards import ValidatorRewardDistributor
from app.modules.blockchain.slash_engine import ValidatorSlashEngine

logger = logging.getLogger(__name__)

CONSENSUS_THRESHOLD = 0.67
MAX_SOURCES = 3


class OracleSettlementBridge:
    """Bridge service to handle oracle consensus and trigger settlement."""

    @classmethod
    async def check_and_settle(cls, match_id: str, db: AsyncSession) -> dict:
        """
        Evaluates current oracle submissions for a match.
        If 67% consensus is reached, triggers settlement.
        """
        # Fetch all results for this match
        result = await db.execute(
            select(OracleResult).where(OracleResult.match_id == match_id)
        )
        all_results = result.scalars().all()

        if not all_results:
            return {"status": "no_results", "match_id": match_id}

        total_count = len(all_results)
        outcome_counts: dict[str, int] = {}
        for r in all_results:
            outcome_counts[r.result] = outcome_counts.get(r.result, 0) + 1

        agreed_outcome: Optional[str] = None
        for outcome, count in outcome_counts.items():
            if (count / total_count) >= CONSENSUS_THRESHOLD:
                agreed_outcome = outcome
                break

        if agreed_outcome:
            # Mark accepted results
            for r in all_results:
                r.is_accepted = (r.result == agreed_outcome)
                r.dispute_flag = False

            await db.flush()

            # Trigger settlement
            return await cls.settle_match(match_id, agreed_outcome, db)

        # Handle dispute if max sources reached and no consensus
        if total_count >= MAX_SOURCES:
            for r in all_results:
                r.dispute_flag = True
            logger.warning(f"Oracle dispute flagged for match {match_id}")
            return {"status": "dispute_flagged", "match_id": match_id}

        return {"status": "pending_consensus", "match_id": match_id, "current_count": total_count}

    @classmethod
    async def settle_match(cls, match_id: str, outcome: str, db: AsyncSession) -> dict:
        """
        Coordinates the core settlement logic and publishes external events.
        """
        # Check if already settled in ConsensusPrediction to avoid double settlement
        cp_res = await db.execute(
            select(ConsensusPrediction).where(ConsensusPrediction.match_id == match_id)
        )
        cp = cp_res.scalar_one_or_none()

        if not cp:
            raise AppError(f"Consensus prediction not found for match {match_id}", status_code=404, code="not_found")

        if cp.status == ConsensusStatus.SETTLED.value:
            return {"status": "already_settled", "match_id": match_id, "outcome": outcome}

        # core_settle_match handles its own internal flushing and notification dispatch.
        # We wrap it in a nested transaction to ensure atomicity.
        async with db.begin_nested():
            try:
                # Core settlement logic (financial mutations)
                settlement = await core_settle_match(match_id, outcome, db)

                # Fetch validator submissions for reward/slash evaluation
                val_preds_res = await db.execute(
                    select(ValidatorPrediction).where(ValidatorPrediction.match_id == match_id)
                )
                val_preds = val_preds_res.scalars().all()

                submissions = []
                consensus_validators = []
                for vp in val_preds:
                    sub = {
                        "validator_id": vp.validator_id,
                        "p_home": vp.p_home,
                        "p_draw": vp.p_draw,
                        "p_away": vp.p_away
                    }
                    submissions.append(sub)

                    # Align check: if they predicted > 50% for the actual outcome, consider them aligned for reward
                    # Actually, the spec in 7.2 says "voted with consensus".
                    # If we use the 30% deviation threshold from slash engine,
                    # alignment means prob_assigned >= 0.7.
                    prob_assigned = getattr(vp, f"p_{outcome}", 0)
                    if prob_assigned >= (1 - ValidatorSlashEngine.DEVIATION_THRESHOLD):
                        consensus_validators.append(vp.validator_id)

                # Distribute rewards
                if consensus_validators:
                    await ValidatorRewardDistributor.distribute(db, match_id, outcome, consensus_validators)

                # Evaluate and execute slashes
                if submissions:
                    await ValidatorSlashEngine.evaluate_slash(db, match_id, outcome, submissions)

                # We do NOT publish the Redis event here because the transaction
                # might still fail at the top level (in the route handler).
                # The bridge returns the settlement details, and the caller
                # should publish the event after db.commit().

                return {
                    "status": "settled",
                    "match_id": match_id,
                    "outcome": outcome,
                    "settlement_id": settlement.id
                }
            except Exception as e:
                logger.error(f"Settlement failed for match {match_id}: {str(e)}")
                raise AppError(f"Settlement execution failed: {str(e)}", status_code=500, code="settlement_error")

    @staticmethod
    async def publish_settlement_event(match_id: str, outcome: str, settlement_id: str):
        """Publishes settlement event to Redis for downstream consumers."""
        try:
            from app.services.cache import _get_redis
            r = _get_redis()

            if r is None:
                from app.config import ENVIRONMENT
                if ENVIRONMENT != "production":
                    from fakeredis import FakeAsyncRedis
                    r = FakeAsyncRedis()
                else:
                    return

            from datetime import datetime, timezone
            payload = {
                "event": "oracle_settled",
                "match_id": match_id,
                "outcome": outcome,
                "settlement_id": settlement_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            await r.publish("vit:oracle:settled", json.dumps(payload))
        except Exception as e:
            logger.error(f"Failed to publish Redis event: {e}")
