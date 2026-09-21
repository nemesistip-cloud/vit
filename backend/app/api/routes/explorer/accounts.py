"""
Explorer Accounts API — account details and transaction history.
"""
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from vit_chain.storage.db import ChainAccount, ChainTransaction

router = APIRouter(prefix="/accounts", tags=["Explorer Accounts"])

# ── Schemas ──────────────────────────────────────────────────────────────────

class AccountDetail(BaseModel):
    address: str
    balance: float
    staked: float
    nonce: int
    tx_count: int
    first_seen: Optional[int]
    last_active: Optional[int]
    node_type: Optional[str]

# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/{address}", response_model=AccountDetail)
async def get_account(
    address: str,
    db: AsyncSession = Depends(get_db)
):
    """Get account overview, including on-chain state and linked node identity."""
    acc_stmt = select(ChainAccount).where(ChainAccount.address == address)
    acc_res = await db.execute(acc_stmt)
    acc = acc_res.scalar_one_or_none()

    if not acc:
        # Check if the address exists in transactions even if not in accounts table yet
        # (Though indexer should ensure account exists)
        raise HTTPException(status_code=404, detail="Account not found")

    # Transaction count
    tx_count_stmt = select(func.count(ChainTransaction.tx_hash)).where(or_(
        ChainTransaction.from_address == address,
        ChainTransaction.to_address == address
    ))
    tx_count = (await db.execute(tx_count_stmt)).scalar() or 0

    # Linked node identity from User table
    user_stmt = select(User).where(User.wallet_address == address)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()

    return {
        "address": acc.address,
        "balance": float(acc.balance or 0),
        "staked": float(acc.staked or 0),
        "nonce": acc.nonce or 0,
        "tx_count": tx_count,
        "first_seen": acc.first_seen_height,
        "last_active": acc.last_active_height,
        "node_type": user.role if user else None
    }

@router.get("/{address}/transactions")
async def list_account_transactions(
    address: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated transaction history for a specific address."""
    stmt = select(ChainTransaction).where(or_(
        ChainTransaction.from_address == address,
        ChainTransaction.to_address == address
    )).order_by(desc(ChainTransaction.timestamp)).limit(limit).offset(offset)

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
