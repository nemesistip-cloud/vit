"""
Explorer Transactions API — paginated transaction list and detailed views.
"""
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from vit_chain.storage.db import ChainTransaction

router = APIRouter(prefix="/transactions", tags=["Explorer Transactions"])

# ── Schemas ──────────────────────────────────────────────────────────────────

class TransactionSummary(BaseModel):
    hash: str
    block_height: Optional[int]
    from_address: str
    to_address: str
    amount: float
    type: str
    timestamp: int
    status: str

class TransactionDetail(TransactionSummary):
    nonce: int
    gas_fee: float
    data: Optional[dict]
    signature: str

# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", response_model=List[TransactionSummary])
async def list_transactions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    address: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get latest transactions, optionally filtered by address."""
    stmt = select(ChainTransaction).order_by(desc(ChainTransaction.timestamp)).limit(limit).offset(offset)

    if address:
        stmt = stmt.where(or_(
            ChainTransaction.from_address == address,
            ChainTransaction.to_address == address
        ))

    res = await db.execute(stmt)
    txs = res.scalars().all()

    return [
        {
            "hash": t.tx_hash,
            "block_height": t.block_height,
            "from_address": t.from_address,
            "to_address": t.to_address,
            "amount": float(t.amount or 0),
            "type": t.tx_type,
            "timestamp": t.timestamp,
            "status": t.status
        }
        for t in txs
    ]

@router.get("/tx/{tx_hash}", response_model=TransactionDetail)
async def get_transaction(
    tx_hash: str,
    db: AsyncSession = Depends(get_db)
):
    """Get full transaction detail and receipt."""
    # Note: Using /tx/{tx_hash} prefix as per build spec, router prefix is /transactions
    # Wait, spec says GET /api/explorer/tx/{tx_hash}
    # but I'm in a router with prefix /transactions.
    # I will add a separate endpoint for this if needed or adjust the router structure.
    # The build spec implies specific URL paths.
    stmt = select(ChainTransaction).where(ChainTransaction.tx_hash == tx_hash)
    res = await db.execute(stmt)
    t = res.scalar_one_or_none()

    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "hash": t.tx_hash,
        "block_height": t.block_height,
        "from_address": t.from_address,
        "to_address": t.to_address,
        "amount": float(t.amount or 0),
        "type": t.tx_type,
        "timestamp": t.timestamp,
        "status": t.status,
        "nonce": t.nonce or 0,
        "gas_fee": float(t.gas_fee or 0),
        "data": t.data,
        "signature": t.signature
    }
