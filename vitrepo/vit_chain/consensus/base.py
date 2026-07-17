import abc
from sqlalchemy.ext.asyncio import AsyncSession
from vit_chain.core.block import VITBlock

class AbstractConsensusEngine(abc.ABC):
    """
    Base interface for all consensus engines (Storage, PoS, etc.)
    """

    @abc.abstractmethod
    def name(self) -> str:
        """Returns the engine name."""
        pass

    @abc.abstractmethod
    async def on_new_block(self, db: AsyncSession, block: VITBlock):
        """Called when a new block is finalized on the chain."""
        pass

    @abc.abstractmethod
    async def validate_block_rules(self, db: AsyncSession, block: VITBlock) -> bool:
        """Consensus-specific block validation rules."""
        pass

    @abc.abstractmethod
    async def produce_block_candidate(self, db: AsyncSession, epoch: int) -> VITBlock:
        """Attempt to produce a block candidate for the current epoch."""
        pass

    @abc.abstractmethod
    async def run_epoch_logic(self, db: AsyncSession, epoch: int):
        """Perform periodic maintenance or challenge logic for this engine."""
        pass
