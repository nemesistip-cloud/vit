import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from vit_chain.consensus.models import Validator, ValidatorReputation
from vit_chain.consensus.registry import ValidatorRegistry

logger = logging.getLogger(__name__)

class ReputationManager:
    """
    Manages validator performance metrics and jailing.
    """
    def __init__(self):
        self.registry = ValidatorRegistry()

    async def record_production(self, db: AsyncSession, node_id: str):
        """Called when a validator successfully produces a block."""
        stmt = select(ValidatorReputation).where(ValidatorReputation.node_id == node_id)
        res = await db.execute(stmt)
        rep = res.scalar_one_or_none()

        if rep:
            rep.blocks_produced += 1
            rep.consecutive_misses = 0
            # Increase score slightly for good behavior
            rep.score = min(1.0, rep.score + 0.01)
            await db.flush()

    async def record_miss(self, db: AsyncSession, node_id: str):
        """Called when a validator misses their slot."""
        stmt = select(ValidatorReputation).where(ValidatorReputation.node_id == node_id)
        res = await db.execute(stmt)
        rep = res.scalar_one_or_none()

        if rep:
            rep.blocks_missed += 1
            rep.consecutive_misses += 1
            # Decrease score
            rep.score = max(0.0, rep.score - 0.05)

            # Auto-jail if 3 consecutive misses
            if rep.consecutive_misses >= 3:
                logger.warning(f"Jailing validator {node_id} due to 3 consecutive misses")
                await self.registry.jail_validator(db, node_id, reason="3 consecutive misses")

            await db.flush()

    async def update_uptime(self, db: AsyncSession, node_id: str, uptime_pct: float):
        """Updates the reported uptime percentage."""
        stmt = update(ValidatorReputation).where(ValidatorReputation.node_id == node_id).values(
            uptime_pct=uptime_pct
        )
        await db.execute(stmt)
        await db.flush()
