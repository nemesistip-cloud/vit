import asyncio, logging, time, json
from app.db.database import AsyncSessionLocal
from vit_chain.consensus.challenge import ChallengeGenerator
from vit_chain.consensus.verifier import ChallengeVerifier
from vit_chain.consensus.voting import VoteCollector
from vit_chain.consensus.producer import BlockProducer
from vit_chain.consensus.finalizer import BlockFinalizer
from vit_chain.consensus.slashing import SlashEngine
from vit_chain.consensus.rewards import StorageRewardCalculator
from app.services.cache import _get_redis
logger = logging.getLogger(__name__)
EPOCH_SECONDS = 15
class ConsensusEngine:
    def __init__(self, validator_key: str):
        self.validator_key = validator_key
        self.generator = ChallengeGenerator(); self.verifier = ChallengeVerifier(); self.collector = VoteCollector()
        self.producer = BlockProducer(); self.finalizer = BlockFinalizer(); self.slash_engine = SlashEngine(); self.reward_calculator = StorageRewardCalculator()
        self._running = False
    async def run(self):
        self._running = True
        while self._running:
            try:
                epoch = int(time.time()) // EPOCH_SECONDS
                async with AsyncSessionLocal() as db:
                    await self.generator.generate_epoch_challenges(db, epoch)
                    await asyncio.sleep(10)
                    results = await self.verifier.collect_epoch_results(db, epoch)
                    if results.get("consensus_weight", 0.0) >= 0.67:
                        block = await self.producer.produce_block(db, epoch, results, self.validator_key)
                        vote_result = await self.collector.collect_votes(db, epoch, block.block_hash)
                        if await self.finalizer.finalize(db, epoch, block, vote_result):
                            rewards = await self.reward_calculator.calculate_epoch_rewards(db, epoch, vote_result.voting_nodes)
                            await self.reward_calculator.distribute_storage_rewards(db, rewards)
                        await self.slash_engine.check_absent_nodes(db, vote_result.absent_nodes, epoch)
                        for node in vote_result.voting_nodes: await self.slash_engine.record_participation(node)
                next_epoch = (int(time.time() // EPOCH_SECONDS) + 1) * EPOCH_SECONDS
                await asyncio.sleep(max(0, next_epoch - time.time()))
            except asyncio.CancelledError: break
            except Exception as e: logger.error(f"Engine error: {e}"); await asyncio.sleep(1)
