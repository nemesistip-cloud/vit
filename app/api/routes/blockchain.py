"""
Unified Blockchain Service API — Public entry point for blockchain platform capabilities.
"""
import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_db
from app.core.kernel import kernel
from vit_chain.core.transaction import VITTransaction
from vit_chain.core.block import VITBlock

router = APIRouter(prefix="/api/chain", tags=["Blockchain Platform"])
logger = logging.getLogger(__name__)

# --- Schemas ---

class TxSubmitRequest(BaseModel):
    from_address: str
    to_address: str
    amount: float
    nonce: int
    timestamp: int
    gas_fee: float
    signature: str
    data: Optional[Dict[str, Any]] = None
    tx_hash: Optional[str] = None

class TxResponse(BaseModel):
    hash: str
    status: str

class BlockHeader(BaseModel):
    height: int
    hash: str
    timestamp: int
    tx_count: int
    validator: str

# --- Endpoints ---

@router.post("/submit", response_model=TxResponse)
async def submit_transaction(tx_data: TxSubmitRequest):
    """Submit a signed VIT transaction to the mempool."""
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.manager:
        raise HTTPException(status_code=503, detail="Blockchain subsystem unavailable")

    tx = VITTransaction(
        from_address=tx_data.from_address,
        to_address=tx_data.to_address,
        amount=Decimal(str(tx_data.amount)),
        nonce=tx_data.nonce,
        timestamp=tx_data.timestamp,
        gas_fee=Decimal(str(tx_data.gas_fee)),
        data=tx_data.data,
        signature=tx_data.signature,
        tx_hash=tx_data.tx_hash or ""
    )

    success = await subsystem.manager.add_transaction(tx)
    if not success:
        raise HTTPException(status_code=400, detail="Transaction rejected (invalid or mempool full)")

    return {"hash": tx.tx_hash, "status": "accepted"}

@router.get("/block/{height_or_hash}")
async def get_block(height_or_hash: str, db: AsyncSession = Depends(get_db)):
    """Retrieve block details by height or hash."""
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.manager:
        raise HTTPException(status_code=503, detail="Blockchain subsystem unavailable")

    if height_or_hash.isdigit():
        block = await subsystem.manager.get_block_by_height(db, int(height_or_hash))
    else:
        # manager currently doesn't have get_block_by_hash directly, but chain does
        block = await subsystem.manager.chain.get_block_by_hash(db, height_or_hash)

    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    return block.to_dict()

@router.get("/latest", response_model=BlockHeader)
async def get_latest_block(db: AsyncSession = Depends(get_db)):
    """Get the most recent block header."""
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.manager:
        raise HTTPException(status_code=503, detail="Blockchain subsystem unavailable")

    latest = await subsystem.manager.get_latest_block(db)
    if not latest:
        raise HTTPException(status_code=404, detail="No blocks found")

    return {
        "height": latest.height,
        "hash": latest.block_hash,
        "timestamp": latest.timestamp,
        "tx_count": latest.tx_count,
        "validator": latest.validator_id
    }

@router.get("/height")
async def get_chain_height(db: AsyncSession = Depends(get_db)):
    """Get current blockchain height."""
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.manager:
        raise HTTPException(status_code=503, detail="Blockchain subsystem unavailable")

    # Using chain directly
    height = await subsystem.manager.chain.chain_height(db)
    return {"height": height}

@router.get("/tx/{tx_hash}")
async def get_transaction(tx_hash: str, db: AsyncSession = Depends(get_db)):
    """Get transaction details and status."""
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.manager:
        raise HTTPException(status_code=503, detail="Blockchain subsystem unavailable")

    # We use the indexer for historical txs
    from vit_chain.storage.db import ChainTransaction
    from sqlalchemy import select

    stmt = select(ChainTransaction).where(ChainTransaction.tx_hash == tx_hash)
    res = await db.execute(stmt)
    tx = res.scalar_one_or_none()

    if tx:
        return {
            "hash": tx.tx_hash,
            "block_height": tx.block_height,
            "from": tx.from_address,
            "to": tx.to_address,
            "amount": float(tx.amount),
            "status": tx.status,
            "timestamp": tx.timestamp
        }

    # Check mempool
    mempool_tx = subsystem.manager.mempool.get(tx_hash)
    if mempool_tx:
        return {
            "hash": mempool_tx.tx_hash,
            "block_height": None,
            "from": mempool_tx.from_address,
            "to": mempool_tx.to_address,
            "amount": float(mempool_tx.amount),
            "status": "pending",
            "timestamp": mempool_tx.timestamp
        }

    raise HTTPException(status_code=404, detail="Transaction not found")
