"""
Explorer Search API — Multi-entity lookup for the block explorer.
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from vit_chain.storage.db import ChainBlock, ChainTransaction, ChainAccount

router = APIRouter(prefix="/search", tags=["Explorer Search"])

@router.get("")
async def search(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for blocks (height or hash), transactions (hash), or accounts (address).
    Returns the type of entity found and its ID/hash.
    """
    q = q.strip()

    # 1. Check if it's a block height (integer)
    if q.isdigit():
        height = int(q)
        stmt = select(ChainBlock.height).where(ChainBlock.height == height)
        res = await db.execute(stmt)
        if res.scalar_one_or_none() is not None:
            return {"type": "block", "id": height, "url": f"/explorer/blocks/{height}"}

    # 2. Check if it's a block hash
    block_stmt = select(ChainBlock.height).where(ChainBlock.block_hash == q)
    res = await db.execute(block_stmt)
    height = res.scalar_one_or_none()
    if height is not None:
        return {"type": "block", "id": height, "url": f"/explorer/blocks/{height}"}

    # 3. Check if it's a transaction hash
    tx_stmt = select(ChainTransaction.tx_hash).where(ChainTransaction.tx_hash == q)
    res = await db.execute(tx_stmt)
    tx_hash = res.scalar_one_or_none()
    if tx_hash:
        return {"type": "transaction", "id": tx_hash, "url": f"/explorer/tx/{tx_hash}"}

    # 4. Check if it's an account address
    acc_stmt = select(ChainAccount.address).where(ChainAccount.address == q)
    res = await db.execute(acc_stmt)
    address = res.scalar_one_or_none()
    if address:
        return {"type": "account", "id": address, "url": f"/explorer/accounts/{address}"}

    # 5. Partial matches for accounts (optional enhancement)
    if len(q) >= 4:
        acc_stmt = select(ChainAccount.address).where(ChainAccount.address.ilike(f"%{q}%")).limit(5)
        res = await db.execute(acc_stmt)
        results = res.scalars().all()
        if results:
            return {
                "type": "suggestions",
                "results": [{"type": "account", "id": addr, "url": f"/explorer/accounts/{addr}"} for addr in results]
            }

    raise HTTPException(status_code=404, detail="No matching blockchain entity found")
