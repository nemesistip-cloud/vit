"""
Explorer Blocks API — paginated block list and detailed block views.
"""
from typing import List, Optional, Union
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.cache import cached
from vit_chain.storage.db import ChainBlock, ChainTransaction

router = APIRouter(prefix="/blocks", tags=["Explorer Blocks"])

@router.get("/stats")
async def get_chain_stats(db: AsyncSession = Depends(get_db)):
    """Get live network statistics (latest block, circulation, etc)."""
    from vit_chain.storage.indexer import ChainIndexer
    from vit_chain.p2p.models import PeerNode

    indexer = ChainIndexer()
    stats = await indexer.get_chain_stats(db)

    # Active nodes from PeerNode
    active_nodes = await db.scalar(select(func.count(PeerNode.node_id)).where(PeerNode.is_active == True)) or 0
    stats["total_nodes"] = active_nodes

    return stats

# ── Schemas ──────────────────────────────────────────────────────────────────

class BlockSummary(BaseModel):
    height: int
    hash: str
    timestamp: int
    tx_count: int
    validator: str
    block_reward: float

class BlockDetail(BlockSummary):
    prev_hash: str
    merkle_root: str
    state_root: str
    total_fees: float
    transactions: List[dict]

# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", response_model=List[BlockSummary])
@cached(ttl=10, key_prefix="explorer:blocks:")
async def list_blocks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Get latest blocks from the chain (cached for 10s)."""
    stmt = select(ChainBlock).order_by(desc(ChainBlock.height)).limit(limit).offset(offset)
    res = await db.execute(stmt)
    blocks = res.scalars().all()

    return [
        {
            "height": b.height,
            "hash": b.block_hash,
            "timestamp": b.timestamp,
            "tx_count": b.tx_count or 0,
            "validator": b.validator_id,
            "block_reward": float(b.block_reward or 0)
        }
        for b in blocks
    ]

@router.get("/{height_or_hash}", response_model=BlockDetail)
async def get_block(
    height_or_hash: str,
    db: AsyncSession = Depends(get_db)
):
    """Get full block details including all transactions."""
    if height_or_hash.isdigit():
        stmt = select(ChainBlock).where(ChainBlock.height == int(height_or_hash))
    else:
        stmt = select(ChainBlock).where(ChainBlock.block_hash == height_or_hash)

    res = await db.execute(stmt)
    block = res.scalar_one_or_none()

    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    # Fetch transactions for this block
    tx_stmt = select(ChainTransaction).where(ChainTransaction.block_height == block.height)
    tx_res = await db.execute(tx_stmt)
    txs = tx_res.scalars().all()

    return {
        "height": block.height,
        "hash": block.block_hash,
        "timestamp": block.timestamp,
        "tx_count": block.tx_count or 0,
        "validator": block.validator_id,
        "block_reward": float(block.block_reward or 0),
        "prev_hash": block.prev_hash,
        "merkle_root": block.merkle_root,
        "state_root": block.state_root,
        "total_fees": float(block.total_fees or 0),
        "transactions": [
            {
                "hash": t.tx_hash,
                "from": t.from_address,
                "to": t.to_address,
                "amount": float(t.amount or 0),
                "type": t.tx_type,
                "status": t.status
            }
            for t in txs
        ]
    }
