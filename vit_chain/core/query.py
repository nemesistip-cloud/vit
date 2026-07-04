import logging
from typing import Optional, List, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, desc
from .block import VITBlock
from ..storage.db import ChainBlock, ChainTransaction, ChainAccount
from app.services.cache import cache

logger = logging.getLogger(__name__)

class BlockchainQueryEngine:
    """
    High-performance query engine for blockchain data.
    Provides multi-entity search and historical lookups.
    """

    async def get_recent_blocks(self, db: AsyncSession, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves a list of recent blocks with basic metadata."""
        cache_key = f"chain:blocks:recent:{limit}:{offset}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            return cached_data

        stmt = select(ChainBlock).order_by(desc(ChainBlock.height)).limit(limit).offset(offset)
        result = await db.execute(stmt)
        blocks = result.scalars().all()

        data = [
            {
                "height": b.height,
                "hash": b.block_hash,
                "timestamp": b.timestamp,
                "tx_count": b.tx_count,
                "validator": b.validator_id,
                "total_fees": str(b.total_fees),
                "reward": str(b.block_reward)
            }
            for b in blocks
        ]

        await cache.set(cache_key, data, ttl=10) # Short TTL for recent blocks
        return data

    async def get_address_history(self, db: AsyncSession, address: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves transaction history for a specific account."""
        cache_key = f"chain:address:txs:{address}:{limit}:{offset}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            return cached_data

        stmt = select(ChainTransaction).where(
            or_(
                ChainTransaction.from_address == address,
                ChainTransaction.to_address == address
            )
        ).order_by(desc(ChainTransaction.timestamp)).limit(limit).offset(offset)

        result = await db.execute(stmt)
        txs = result.scalars().all()

        data = [
            {
                "hash": tx.tx_hash,
                "block_height": tx.block_height,
                "from": tx.from_address,
                "to": tx.to_address,
                "amount": str(tx.amount),
                "timestamp": tx.timestamp,
                "status": tx.status,
                "type": tx.tx_type
            }
            for tx in txs
        ]

        await cache.set(cache_key, data, ttl=30)
        return data

    async def unified_search(self, db: AsyncSession, q: str) -> Dict[str, Any]:
        """
        Performs a unified search across blocks, transactions, and accounts.
        Returns the entity type and its specific summary.
        """
        q = q.strip()

        # 1. Check Block Height
        if q.isdigit():
            height = int(q)
            stmt = select(ChainBlock).where(ChainBlock.height == height)
            res = await db.execute(stmt)
            b = res.scalar_one_or_none()
            if b:
                return {
                    "type": "block",
                    "id": b.height,
                    "summary": f"Block #{b.height} ({b.tx_count} txs)",
                    "url": f"/explorer/blocks/{b.height}"
                }

        # 2. Check Block Hash
        stmt = select(ChainBlock).where(ChainBlock.block_hash == q)
        res = await db.execute(stmt)
        b = res.scalar_one_or_none()
        if b:
            return {
                "type": "block",
                "id": b.height,
                "summary": f"Block #{b.height} - {b.block_hash[:16]}...",
                "url": f"/explorer/blocks/{b.height}"
            }

        # 3. Check Transaction Hash
        stmt = select(ChainTransaction).where(ChainTransaction.tx_hash == q)
        res = await db.execute(stmt)
        tx = res.scalar_one_or_none()
        if tx:
            return {
                "type": "transaction",
                "id": tx.tx_hash,
                "summary": f"Transaction {tx.tx_hash[:16]}... ({tx.status})",
                "url": f"/explorer/tx/{tx.tx_hash}"
            }

        # 4. Check Account Address
        stmt = select(ChainAccount).where(ChainAccount.address == q)
        res = await db.execute(stmt)
        acc = res.scalar_one_or_none()
        if acc:
            return {
                "type": "account",
                "id": acc.address,
                "summary": f"Account {acc.address[:16]}... Balance: {acc.balance} VIT",
                "url": f"/explorer/accounts/{acc.address}"
            }

        # 5. Fallback: Search by prefix (only for accounts for now)
        if len(q) >= 4:
            stmt = select(ChainAccount).where(ChainAccount.address.ilike(f"%{q}%")).limit(5)
            res = await db.execute(stmt)
            results = res.scalars().all()
            if results:
                return {
                    "type": "suggestions",
                    "results": [
                        {
                            "type": "account",
                            "id": a.address,
                            "summary": a.address,
                            "url": f"/explorer/accounts/{a.address}"
                        }
                        for a in results
                    ]
                }

        return {"type": "not_found", "query": q}

    async def get_chain_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        """Aggregation of chain performance and economic metrics."""
        cache_key = "chain:metrics"
        cached_data = await cache.get(cache_key)
        if cached_data:
            return cached_data

        total_blocks = await db.scalar(select(func.count(ChainBlock.height))) or 0
        total_txs = await db.scalar(select(func.count(ChainTransaction.tx_hash))) or 0
        total_accounts = await db.scalar(select(func.count(ChainAccount.address))) or 0
        circulating_supply = await db.scalar(select(func.sum(ChainAccount.balance))) or 0

        # Last 24h stats
        one_day_ago = int(func.now().cast(func.Integer)) - 86400 # Approximation
        # Real timestamp comparison would be better if we had it properly in SQL

        data = {
            "total_blocks": total_blocks,
            "total_transactions": total_txs,
            "total_accounts": total_accounts,
            "circulating_supply": str(circulating_supply),
            "tps_last_hour": 0.0 # Placeholder
        }

        await cache.set(cache_key, data, ttl=300)
        return data
