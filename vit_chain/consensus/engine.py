import asyncio
import logging
import time
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from vit_chain.consensus.storage_engine import StorageConsensusEngine
from vit_chain.consensus.base import AbstractConsensusEngine
from vit_chain.consensus.reputation import ReputationManager
from vit_chain.consensus.events import ConsensusEventBus
from vit_chain.consensus.models import ConsensusCheckpoint
from vit_chain.core.blockchain import VITChain

logger = logging.getLogger(__name__)
EPOCH_SECONDS = 15
CHECKPOINT_INTERVAL = 100

class ConsensusManager:
    """
    Coordinates multiple consensus engines and manages the validator lifecycle.
    """
    def __init__(self, validator_key: str):
        self.validator_key = validator_key
        self.engines: dict[str, AbstractConsensusEngine] = {
            "storage": StorageConsensusEngine(validator_key)
        }
        self.primary_engine = "storage"
        self.reputation_manager = ReputationManager()
        self.event_bus = ConsensusEventBus()
        self._running = False

    async def run(self):
        self._running = True
        logger.info(f"ConsensusManager started with engines: {list(self.engines.keys())}")

        while self._running:
            try:
                epoch = int(time.time()) // EPOCH_SECONDS

                # 1. Start Epoch logic (Generates challenges etc.)
                async with AsyncSessionLocal() as db:
                    for engine in self.engines.values():
                        await engine.run_epoch_logic(db, epoch)
                    await db.commit() # Persist challenges

                # Release DB session during network wait period
                await asyncio.sleep(10)

                # 2. Block Production and Finalization phase
                async with AsyncSessionLocal() as db:
                    engine = self.engines.get(self.primary_engine)
                    if engine:
                        block = await engine.produce_block_candidate(db, epoch)
                        if block:
                            if hasattr(engine, 'finalize_block'):
                                success = await engine.finalize_block(db, epoch, block)
                                if success:
                                    await self.reputation_manager.record_production(db, block.validator_id)
                                    await self.event_bus.emit_block_produced(
                                        block.height, block.block_hash, block.validator_id
                                    )
                                    if block.height > 0 and block.height % CHECKPOINT_INTERVAL == 0:
                                        await self.create_checkpoint(db, block)

                                    await db.commit() # Finalize all changes
                                    logger.info(f"Block finalized at height {block.height}")
                                else:
                                    # Record miss if finalization fails
                                    if block.validator_id:
                                        await self.reputation_manager.record_miss(db, block.validator_id)
                                        await db.commit()
                                    logger.warning(f"Block finalization failed for epoch {epoch}")
                        else:
                            # Potential slot miss - logic to identify whose slot it was would go here
                            pass

                now = time.time()
                next_epoch_time = (int(now // EPOCH_SECONDS) + 1) * EPOCH_SECONDS
                await asyncio.sleep(max(0, next_epoch_time - now))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"ConsensusManager error: {e}")
                await asyncio.sleep(1)

    async def create_checkpoint(self, db: AsyncSession, block):
        """Creates a state checkpoint at the current block."""
        checkpoint = ConsensusCheckpoint(
            height=block.height,
            block_hash=block.block_hash,
            state_root=block.merkle_root,
            validator_set_hash="0x" + "f"*64
        )
        db.add(checkpoint)
        # commit() is handled by the caller

    async def validate_block(self, db: AsyncSession, block) -> bool:
        """Runs validation across all engines."""
        for engine in self.engines.values():
            if not await engine.validate_block_rules(db, block):
                return False
        return True

    async def on_new_block(self, db: AsyncSession, block):
        """Notify all engines and update reputation."""
        for engine in self.engines.values():
            await engine.on_new_block(db, block)

        if block.validator_id:
            await self.reputation_manager.record_production(db, block.validator_id)

        await db.commit()

    def stop(self):
        self._running = False
