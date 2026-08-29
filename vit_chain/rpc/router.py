from fastapi import APIRouter, Depends, Request, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List
from pydantic import BaseModel
from app.db.database import get_db
from .server import VITChainRPC
from vit_chain.storage.db import ChainBlock, ChainTransaction, ChainAccount
from app.core.kernel import kernel

router = APIRouter(tags=["Chain"])
rpc_server = VITChainRPC()

# ── Schemas ──────────────────────────────────────────────────────────────────

class BlockSummary(BaseModel):
    height: int
    hash: str
    timestamp: int
    tx_count: int
    validator: str
    block_reward: float
    
    class Config:
        from_attributes = True

class TransactionSummary(BaseModel):
    hash: str
    from_address: str
    to_address: str
    amount: str
    timestamp: int
    block_height: Optional[int]
    status: str
    
    class Config:
        from_attributes = True

class AccountSummary(BaseModel):
    address: str
    balance: str
    nonce: int
    
    class Config:
        from_attributes = True

# ── RPC Endpoint ─────────────────────────────────────────────────────────────

@router.post("/chain/rpc")
async def rpc_endpoint(request: Request, db: AsyncSession = Depends(get_db)):
    """Accepts JSON-RPC 2.0 request body"""
    body = await request.json()
    response = await rpc_server.handle(body, db)
    return response

@router.get("/chain/rpc/health")
async def rpc_health():
    """For MetaMask health check"""
    return {
        "status": "ok",
        "chain_id": 7764,
        "name": "VIT Chain"
    }

# ── REST Explorer Endpoints ──────────────────────────────────────────────────

@router.get("/blocks", response_model=List[BlockSummary])
async def get_blocks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Get latest blocks from the chain.
    Frontend calls: GET /api/blocks?limit=5
    """
    try:
        stmt = (
            select(ChainBlock)
            .order_by(desc(ChainBlock.height))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        blocks = result.scalars().all()
        
        return [
            {
                "height": b.height,
                "hash": b.block_hash or "0x0",
                "timestamp": b.timestamp or 0,
                "tx_count": b.tx_count or 0,
                "validator": b.validator_id or "unknown",
                "block_reward": float(b.block_reward or 0),
            }
            for b in blocks
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch blocks: {str(e)}")

@router.get("/blocks/{height}", response_model=BlockSummary)
async def get_block(
    height: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific block by height."""
    try:
        stmt = select(ChainBlock).where(ChainBlock.height == height)
        result = await db.execute(stmt)
        block = result.scalar_one_or_none()
        
        if not block:
            raise HTTPException(status_code=404, detail=f"Block {height} not found")
        
        return {
            "height": block.height,
            "hash": block.block_hash or "0x0",
            "timestamp": block.timestamp or 0,
            "tx_count": block.tx_count or 0,
            "validator": block.validator_id or "unknown",
            "block_reward": float(block.block_reward or 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch block: {str(e)}")

@router.get("/transactions", response_model=List[TransactionSummary])
async def get_transactions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Get latest transactions from the chain."""
    try:
        stmt = (
            select(ChainTransaction)
            .order_by(desc(ChainTransaction.timestamp))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        txs = result.scalars().all()
        
        return [
            {
                "hash": tx.tx_hash or "0x0",
                "from_address": tx.from_address or "",
                "to_address": tx.to_address or "",
                "amount": str(tx.amount or 0),
                "timestamp": tx.timestamp or 0,
                "block_height": tx.block_height,
                "status": tx.status or "pending",
            }
            for tx in txs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch transactions: {str(e)}")

@router.get("/transactions/{tx_hash}", response_model=TransactionSummary)
async def get_transaction(
    tx_hash: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific transaction by hash."""
    try:
        stmt = select(ChainTransaction).where(ChainTransaction.tx_hash == tx_hash)
        result = await db.execute(stmt)
        tx = result.scalar_one_or_none()
        
        if not tx:
            raise HTTPException(status_code=404, detail=f"Transaction {tx_hash} not found")
        
        return {
            "hash": tx.tx_hash or "0x0",
            "from_address": tx.from_address or "",
            "to_address": tx.to_address or "",
            "amount": str(tx.amount or 0),
            "timestamp": tx.timestamp or 0,
            "block_height": tx.block_height,
            "status": tx.status or "pending",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch transaction: {str(e)}")

@router.get("/addresses/{address}", response_model=AccountSummary)
async def get_address(
    address: str,
    db: AsyncSession = Depends(get_db)
):
    """Get account details and balance."""
    try:
        stmt = select(ChainAccount).where(ChainAccount.address == address)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail=f"Address {address} not found")
        
        return {
            "address": account.address,
            "balance": str(account.balance or 0),
            "nonce": account.nonce or 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch address: {str(e)}")
