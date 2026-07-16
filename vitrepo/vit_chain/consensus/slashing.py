import logging
import json
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.services.cache import _get_redis
from app.modules.storage_verification.models import UserStorageNode
from app.modules.blockchain.models import ValidatorSlashEvent, ValidatorProfile
from app.db.models import User

logger = logging.getLogger(__name__)

SLASH_THRESHOLD = 3
SLASH_AMOUNT_PCT = 0.1

class SlashEngine:
    async def check_absent_nodes(self, db: AsyncSession,
                                  absent_nodes: list[str],
                                  epoch: int):
        """
        Track missed epochs in Redis. Slash nodes that exceed the threshold.
        """
        r = _get_redis()
        if not r:
            return

        for node_id in absent_nodes:
            key = f"vit:node:misses:{node_id}"
            try:
                # Increment consecutive misses
                misses = await r.incr(key)

                if misses >= SLASH_THRESHOLD:
                    logger.warning(f"[consensus] Node {node_id} exceeded miss threshold ({misses}). Executing slash.")
                    await self._execute_slash(db, node_id, epoch)
                    # Reset counter after slash
                    await r.set(key, 0)
            except Exception as e:
                logger.error(f"[consensus] Slashing check failed for node {node_id}: {e}")

    async def record_participation(self, node_id: str):
        """Reset miss counter for nodes that participated in consensus."""
        r = _get_redis()
        if r:
            await r.set(f"vit:node:misses:{node_id}", 0)

    async def _execute_slash(self, db: AsyncSession, node_id: str, epoch: int):
        """Reduces node stake by SLASH_AMOUNT_PCT and marks as degraded."""
        # 1. Find the validator profile and linked user
        stmt = (
            select(ValidatorProfile, User.id.label("user_id"))
            .join(User, ValidatorProfile.user_id == User.id)
            .where(User.wallet_address == node_id)
        )
        result = await db.execute(stmt)
        row = result.one_or_none()

        if not row:
            logger.warning(f"No validator profile found for address {node_id} to slash")
            return

        profile, user_id = row
        old_stake = profile.stake_amount
        slash_amount = old_stake * Decimal(str(SLASH_AMOUNT_PCT))
        new_stake = old_stake - slash_amount

        # 2. Update profile stake
        profile.stake_amount = new_stake

        # 3. Log slash event
        event = ValidatorSlashEvent(
            validator_id=profile.id,
            user_id=user_id,
            slash_reason=f"Missed {SLASH_THRESHOLD} consecutive epochs (final epoch: {epoch})",
            slash_pct=Decimal(str(SLASH_AMOUNT_PCT)),
            slash_amount=slash_amount,
            stake_before=old_stake,
            stake_after=new_stake,
            trust_score_at_slash=profile.trust_score
        )
        db.add(event)

        # 4. Mark node as "degraded" in storage swarm
        await db.execute(
            update(UserStorageNode)
            .where(UserStorageNode.user_id == user_id)
            .values(status="degraded")
        )

        # 5. Persist changes
        await db.commit()

        # 6. Notify network
        r = _get_redis()
        if r:
            await r.publish(f"vit:consensus:slashed:{node_id}", json.dumps({
                "node_id": node_id,
                "slash_amount": str(slash_amount),
                "reason": "inactivity"
            }))

        logger.info(f"Slashed node {node_id}: {slash_amount} VIT removed from stake")
