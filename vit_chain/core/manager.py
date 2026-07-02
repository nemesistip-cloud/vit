import logging
import asyncio
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from .block import VITBlock, validate_block, build_block
from .transaction import VITTransaction, Mempool
from .chain import VITChain
from .state import ChainState
from ..storage.indexer import ChainIndexer
from app.core.event_bus import event_bus

logger = logging.getLogger(__name__)

class BlockchainManager:
    """
    Central coordinator for the VIT Blockchain runtime.
    Manages the chain, mempool, and ledger synchronization.
    """
    def __init__(self, mempool_size: int = 5000, tx_ttl: int = 3600):
        self.chain = VITChain()
        self.mempool = Mempool(max_size=mempool_size, tx_ttl=tx_ttl)
        self.state = ChainState()
        self.indexer = ChainIndexer()
        self._lock = asyncio.Lock()

    async def get_latest_block(self, db: AsyncSession) -> Optional[VITBlock]:
        return await self.chain.get_latest_block(db)

    async def get_block_by_height(self, db: AsyncSession, height: int) -> Optional[VITBlock]:
        return await self.chain.get_block_by_height(db, height)

    async def add_transaction(self, tx: VITTransaction) -> bool:
        """Adds transaction to mempool if valid."""
        success = self.mempool.add(tx)
        if success:
            await event_bus.publish("TransactionAccepted", tx.to_dict(), sender="blockchain_manager")
        else:
            await event_bus.publish("TransactionRejected", tx.to_dict(), sender="blockchain_manager")
        return success

    async def process_new_block(self, db: AsyncSession, block: VITBlock) -> bool:
        """
        Validates and appends a new block to the ledger.
        Updates state and indexes the block.
        """
        async with self._lock:
            # 1. Basic validation
            latest = await self.chain.get_latest_block(db)
            if not validate_block(block, latest, []):
                logger.error(f"[blockchain] Block validation failed for height {block.height}")
                return False

            # 2. Add to chain (persists as IoTEvent via VITChain.add_block)
            # and applies state changes (ChainState.apply_transaction)
            success = await self.chain.add_block(db, block)
            if not success:
                logger.error(f"[blockchain] Failed to add block {block.height} to chain")
                return False

            # 3. Index for rich queries (ChainIndexer)
            state_root = await self.state.get_state_root(db)
            await self.indexer.index_block(db, block, state_root=state_root)

            # 4. Clean up mempool
            tx_hashes = [tx.tx_hash for tx in block.transactions]
            self.mempool.remove(tx_hashes)

            # 5. Emit events
            await event_bus.publish("BlockAdded", {
                "height": block.height,
                "hash": block.block_hash,
                "tx_count": block.tx_count,
                "validator": block.validator_id
            }, sender="blockchain_manager")

            return True

    async def verify_chain_integrity(self, db: AsyncSession) -> bool:
        """
        Verifies the full chain by traversing from genesis.
        Checks block hashes, previous hash links, and Merkle roots.
        """
        height = await self.chain.chain_height(db)
        if height < 0:
            return True # Empty chain is valid

        prev_block = None
        for h in range(height + 1):
            block = await self.chain.get_block_by_height(db, h)
            if not block:
                logger.error(f"[blockchain] Integrity check failed: missing block at height {h}")
                return False

            # validate_block handles hash, prev_hash, merkle_root, and signature
            if not validate_block(block, prev_block, []):
                logger.error(f"[blockchain] Integrity check failed: validation failed at height {h}")
                return False

            prev_block = block

        await event_bus.publish("LedgerVerified", {"height": height}, sender="blockchain_manager")
        return True

    async def get_mempool_stats(self) -> Dict[str, Any]:
        return {
            "size": self.mempool.size(),
            "max_size": self.mempool.max_size,
            "tx_ttl": self.mempool.tx_ttl
        }
