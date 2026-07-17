import logging
import asyncio
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .block import VITBlock, validate_block
from .transaction import VITTransaction, Mempool
from .chain import VITChain
from .state import ChainState
from ..storage.indexer import ChainIndexer
from ..storage.db import ChainTransaction
from app.core.event_bus import event_bus
from app.services.cache import cache

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
        """Returns the most recent block, utilizing cache for performance."""
        cached_block_dict = await cache.get("chain:latest_block")
        if cached_block_dict:
            # Note: We return None to force refresh if full VITBlock object is needed,
            # as re-hydration is complex. However, API callers often use the dict directly.
            pass

        block = await self.chain.get_latest_block(db)
        if block:
            await cache.set("chain:latest_block", block.to_dict(), ttl=5)
        return block

    async def get_block_by_height(self, db: AsyncSession, height: int) -> Optional[VITBlock]:
        """Returns block at specific height, utilizing cache."""
        cache_key = f"chain:block:height:{height}"
        cached_dict = await cache.get(cache_key)
        if cached_dict:
            # We still fetch from DB to return a proper VITBlock object,
            # but we update the cache.
            pass

        block = await self.chain.get_block_by_height(db, height)
        if block:
            await cache.set(cache_key, block.to_dict(), ttl=60)
        return block

    async def get_block_by_hash(self, db: AsyncSession, block_hash: str) -> Optional[VITBlock]:
        """Returns block by hash, utilizing cache."""
        cache_key = f"chain:block:hash:{block_hash}"
        cached_dict = await cache.get(cache_key)
        if cached_dict:
            pass

        block = await self.chain.get_block_by_hash(db, block_hash)
        if block:
            await cache.set(cache_key, block.to_dict(), ttl=60)
        return block

    async def get_transaction(self, db: AsyncSession, tx_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a transaction by hash.
        Checks mempool first (pending), then the historical indexer.
        """
        # 1. Check Mempool
        mempool_tx = self.mempool.get(tx_hash)
        if mempool_tx:
            data = mempool_tx.to_dict()
            data["status"] = "pending"
            return data

        # 2. Check Indexer (via direct DB query for now)
        stmt = select(ChainTransaction).where(ChainTransaction.tx_hash == tx_hash)
        res = await db.execute(stmt)
        ctx = res.scalar_one_or_none()
        if ctx:
            return {
                "tx_hash": ctx.tx_hash,
                "block_height": ctx.block_height,
                "from_address": ctx.from_address,
                "to_address": ctx.to_address,
                "amount": str(ctx.amount),
                "nonce": ctx.nonce,
                "gas_fee": str(ctx.gas_fee),
                "timestamp": ctx.timestamp,
                "status": ctx.status,
                "data": ctx.data
            }

        return None

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

            # 2. Add to chain
            success = await self.chain.add_block(db, block)
            if not success:
                logger.error(f"[blockchain] Failed to add block {block.height} to chain")
                return False

            # 3. Index for rich queries
            state_root = await self.state.get_state_root(db)
            await self.indexer.index_block(db, block, state_root=state_root)

            # 4. Clean up mempool
            tx_hashes = [tx.tx_hash for tx in block.transactions]
            self.mempool.remove(tx_hashes)

            # 5. Invalidate relevant caches
            await cache.delete("chain:latest_block")
            await cache.delete("chain:metrics")

            # 6. Emit events
            await event_bus.publish("BlockAdded", {
                "height": block.height,
                "hash": block.block_hash,
                "tx_count": block.tx_count,
                "validator": block.validator_id
            }, sender="blockchain_manager")

            return True

    async def verify_chain_integrity(self, db: AsyncSession) -> bool:
        """Verifies the full chain by traversing from genesis."""
        height = await self.chain.chain_height(db)
        if height < 0:
            return True

        prev_block = None
        for h in range(height + 1):
            block = await self.chain.get_block_by_height(db, h)
            if not block:
                logger.error(f"[blockchain] Integrity check failed: missing block at height {h}")
                return False

            if not validate_block(block, prev_block, []):
                logger.error(f"[blockchain] Integrity check failed: validation failed at height {h}")
                return False

            prev_block = block

        await event_bus.publish("LedgerVerified", {"height": height}, sender="blockchain_manager")
        return True

    async def get_mempool_stats(self) -> Dict[str, Any]:
        """Provides real-time mempool telemetry."""
        return {
            "size": self.mempool.size(),
            "max_size": self.mempool.max_size,
            "tx_ttl": self.mempool.tx_ttl,
            "usage_pct": (self.mempool.size() / self.mempool.max_size) * 100 if self.mempool.max_size > 0 else 0
        }
