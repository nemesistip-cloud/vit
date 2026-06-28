import json
import logging
from decimal import Decimal
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cache import _get_redis
from vit_chain.consensus.voting import VoteResult

logger = logging.getLogger(__name__)

class BlockFinalizer:
    async def finalize(self, db: AsyncSession,
                       epoch: int,
                       block: Any,
                       vote_result: VoteResult) -> bool:
        """
        If consensus reached: commit block, distribute rewards, notify network.
        Uses duck-typing for block/chain components to be implemented in Track 1.
        """
        r = _get_redis()

        if vote_result.consensus_reached:
            try:
                # 1. Attach signatures to block
                if hasattr(block, "consensus_votes"):
                    block.consensus_votes = vote_result.voting_nodes

                # 2. Persist block to chain (Track 1 dependency)
                # In actual impl: await VITChain().add_block(db, block)
                logger.info(f"[consensus] Finalizing block {vote_result.block_hash} for epoch {epoch}")

                # 3. Distribute rewards
                await self.distribute_block_rewards(db, block, vote_result)

                # 4. Clean Mempool (Track 1 dependency)
                # In actual impl: Mempool().remove_transactions(block.transactions)

                # 5. Publish finalized event
                if r:
                    payload = {
                        "height": getattr(block, "height", 0),
                        "block_hash": vote_result.block_hash,
                        "epoch": epoch,
                        "tx_count": len(getattr(block, "transactions", [])),
                        "nodes_rewarded": len(vote_result.voting_nodes) + 1 # Voters + Producer
                    }
                    await r.publish("vit:chain:block_finalized", json.dumps(payload))

                return True

            except Exception as e:
                logger.error(f"[consensus] Finalization error at epoch {epoch}: {e}", exc_info=True)
                await db.rollback()
                return False
        else:
            logger.warning(f"[consensus] Consensus failed for epoch {epoch} (Weight: {vote_result.valid_votes}/{vote_result.total_nodes})")
            if r:
                await r.publish(f"vit:consensus:failed:{epoch}", json.dumps({"epoch": epoch, "reason": "insufficient_votes"}))
            return False

    async def distribute_block_rewards(self, db: AsyncSession,
                                        block: Any,
                                        vote_result: VoteResult):
        """
        Calculates and applies block rewards.
        40% to producer, 60% split among voting nodes.
        """
        # BASE_REWARD could come from PlatformConfig or default
        BASE_REWARD = Decimal("10.0")
        producer_share = BASE_REWARD * Decimal("0.4")
        voter_pool = BASE_REWARD * Decimal("0.6")

        if not vote_result.voting_nodes:
            return

        per_voter = voter_pool / len(vote_result.voting_nodes)

        # Apply rewards inside a transaction block
        async with db.begin_nested():
            # Apply to producer
            producer_addr = getattr(block, "validator_id", None)
            if producer_addr:
                await self._apply_reward(db, producer_addr, producer_share, "producer", vote_result.block_hash)

            # Apply to voters
            for addr in vote_result.voting_nodes:
                await self._apply_reward(db, addr, per_voter, "voter", vote_result.block_hash)

    async def _apply_reward(self, db: AsyncSession, address: str, amount: Decimal, role: str, block_hash: str):
        """
        Applies reward to a specific node and publishes event.
        Implementation depends on Track 1's ChainState.
        """
        # In actual impl: await ChainState().apply_block_reward(db, address, amount)
        logger.debug(f"[consensus] Rewarding {role} {address} with {amount} VIT")

        r = _get_redis()
        if r:
            payload = {
                "address": address,
                "amount": str(amount),
                "role": role,
                "block_hash": block_hash
            }
            await r.publish(f"vit:node:rewarded:{address}", json.dumps(payload))
