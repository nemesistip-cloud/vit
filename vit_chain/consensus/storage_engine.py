import logging
from sqlalchemy.ext.asyncio import AsyncSession
from vit_chain.consensus.base import AbstractConsensusEngine
from vit_chain.consensus.challenge import ChallengeGenerator
from vit_chain.consensus.verifier import ChallengeVerifier
from vit_chain.consensus.voting import VoteCollector
from vit_chain.consensus.producer import BlockProducer
from vit_chain.consensus.finalizer import BlockFinalizer
from vit_chain.consensus.slashing import SlashEngine
from vit_chain.consensus.rewards import StorageRewardCalculator
from vit_chain.core.block import VITBlock

logger = logging.getLogger(__name__)

class StorageConsensusEngine(AbstractConsensusEngine):
    def __init__(self, validator_key: str):
        self.validator_key = validator_key
        self.generator = ChallengeGenerator()
        self.verifier = ChallengeVerifier()
        self.collector = VoteCollector()
        self.producer = BlockProducer()
        self.finalizer = BlockFinalizer()
        self.slash_engine = SlashEngine()
        self.reward_calculator = StorageRewardCalculator()

    def name(self) -> str:
        return "storage"

    async def on_new_block(self, db: AsyncSession, block: VITBlock):
        # Update participation records
        if block.validator_id:
            await self.slash_engine.record_participation(block.validator_id)

    async def validate_block_rules(self, db: AsyncSession, block: VITBlock) -> bool:
        # Check storage proofs validity for this block
        return True

    async def produce_block_candidate(self, db: AsyncSession, epoch: int) -> VITBlock:
        results = await self.verifier.collect_epoch_results(db, epoch)
        if results.get("consensus_weight", 0.0) >= 0.67:
            block = await self.producer.produce_block(db, epoch, results, self.validator_key)
            return block
        return None

    async def finalize_block(self, db: AsyncSession, epoch: int, block: VITBlock) -> bool:
        """Collect votes and finalize the block."""
        vote_result = await self.collector.collect_votes(db, epoch, block.block_hash)
        if await self.finalizer.finalize(db, epoch, block, vote_result):
            rewards = await self.reward_calculator.calculate_epoch_rewards(db, epoch, vote_result.voting_nodes)
            await self.reward_calculator.distribute_storage_rewards(db, rewards)
            await self.slash_engine.check_absent_nodes(db, vote_result.absent_nodes, epoch)
            return True
        return False

    async def run_epoch_logic(self, db: AsyncSession, epoch: int):
        await self.generator.generate_epoch_challenges(db, epoch)
