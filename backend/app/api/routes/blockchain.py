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
    """Retrieve block details by height or hash using the SDK/Manager."""
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.manager:
        raise HTTPException(status_code=503, detail="Blockchain subsystem unavailable")

    sdk = subsystem.get_sdk()
    block_dict = await sdk.get_block(db, height_or_hash)

    if not block_dict:
        raise HTTPException(status_code=404, detail="Block not found")

    return block_dict

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

    height = await subsystem.manager.chain.chain_height(db)
    return {"height": height}

@router.get("/tx/{tx_hash}")
async def get_transaction(tx_hash: str, db: AsyncSession = Depends(get_db)):
    """Get transaction details and status using the SDK."""
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.manager:
        raise HTTPException(status_code=503, detail="Blockchain subsystem unavailable")

    sdk = subsystem.get_sdk()
    tx = await sdk.get_transaction(db, tx_hash)

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return tx

@router.get("/transactions")
async def get_recent_transactions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves recent chain transactions via the Query Engine."""
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.query_engine:
        raise HTTPException(status_code=503, detail="Blockchain query engine unavailable")

    # Fetch recent transactions across blocks
    from sqlalchemy import select, desc
    from vit_chain.models import ChainTransaction
    result = await db.execute(
        select(ChainTransaction).order_by(desc(ChainTransaction.block_height)).offset(offset).limit(limit)
    )
    txs = result.scalars().all()
    tx_list = [
        {
            "tx_hash": tx.tx_hash,
            "sender": tx.sender,
            "recipient": tx.recipient,
            "amount": str(tx.amount),
            "fee": str(tx.fee),
            "payload": tx.payload,
            "timestamp": tx.timestamp,
            "block_height": tx.block_height,
        }
        for tx in txs
    ]
    return {"transactions": tx_list, "total": len(tx_list)}

@router.get("/recent-blocks")
async def get_recent_blocks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves a list of recent blocks via the Query Engine."""
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.query_engine:
        raise HTTPException(status_code=503, detail="Blockchain query engine unavailable")

    return await subsystem.query_engine.get_recent_blocks(db, limit, offset)

@router.get("/address/{address}/history")
async def get_address_history(
    address: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves transaction history for an address via the Query Engine."""
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.query_engine:
        raise HTTPException(status_code=503, detail="Blockchain query engine unavailable")

    return await subsystem.query_engine.get_address_history(db, address, limit, offset)

@router.get("/metrics")
async def get_chain_metrics(db: AsyncSession = Depends(get_db)):
    """Retrieves high-level blockchain metrics."""
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.query_engine:
        raise HTTPException(status_code=503, detail="Blockchain query engine unavailable")

    return await subsystem.query_engine.get_chain_metrics(db)
