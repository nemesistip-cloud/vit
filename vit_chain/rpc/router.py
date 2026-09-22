import time
from fastapi import APIRouter, Depends, Request, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.db.database import get_db
from .server import VITChainRPC
from vit_chain.storage.db import ChainBlock, ChainTransaction, ChainAccount
from app.core.kernel import kernel

router = APIRouter(tags=["Chain"])
rpc_server = VITChainRPC()

# ── Schemas ──────────────────────────────────────────────────────────────────

class BlockSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    height: int
    hash: str
    timestamp: int
    tx_count: int
    validator: str
    block_reward: float
    
class TransactionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hash: str
    from_address: str
    to_address: str
    amount: str
    timestamp: int
    block_height: Optional[int]
    status: str
    
class AccountSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    address: str
    balance: str
    nonce: int
    
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

@router.get("/api/status")
async def get_status(db: AsyncSession = Depends(get_db)):
    """Canonical chain status payload used by the read-only VIT Chain SDK."""
    try:
        latest = await db.scalar(
            select(ChainBlock).order_by(desc(ChainBlock.height)).limit(1)
        )
        active_validators = await db.scalar(select(func.count(ChainAccount.address))) or 0
        return {
            "network": "testnet",
            "chain_id": 7764,
            "node_version": "1.0.0",
            "block_height": latest.height if latest else 0,
            "latest_block_hash": latest.block_hash if latest else "0x0",
            "latest_block_ts": latest.timestamp if latest else 0,
            "epoch_seconds": 15,
            "active_validators": active_validators,
            "connected_peers": 0,
            "server_time": int(time.time()),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chain status: {str(exc)}") from exc

@router.get("/api/blocks/latest")
async def get_latest_block_rest(db: AsyncSession = Depends(get_db)):
    """Read the most recent canonical block header."""
    try:
        block = await db.scalar(select(ChainBlock).order_by(desc(ChainBlock.height)).limit(1))
        if not block:
            raise HTTPException(status_code=404, detail="No chain blocks found")
        return {
            "height": block.height,
            "block_hash": block.block_hash,
            "prev_hash": block.prev_hash,
            "merkle_root": block.merkle_root,
            "timestamp": block.timestamp,
            "validator_id": block.validator_id,
            "tx_count": block.tx_count or 0,
            "total_fees": str(block.total_fees or 0),
            "block_reward": str(block.block_reward or 0),
            "validator_signature": block.validator_signature,
            "storage_proofs": [],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch latest block: {str(exc)}") from exc

@router.get("/api/validators")
async def get_validators(db: AsyncSession = Depends(get_db)):
    """Canonical validator registry for the standalone chain API contract."""
    try:
        rows = (await db.execute(select(ChainAccount).order_by(ChainAccount.address).limit(100))).scalars().all()
        validators = [
            {
                "node_id": row.address,
                "address": row.address,
                "name": "genesis-validator" if row.address else "validator",
                "stake": str(row.staked or 0),
                "status": "active" if (row.staked or 0) > 0 else "inactive",
            }
            for row in rows
        ]
        return {"count": len(validators), "validators": validators}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch validators: {str(exc)}") from exc

@router.get("/api/accounts/{address}")
async def get_chain_account(address: str, db: AsyncSession = Depends(get_db)):
    """Return canonical account state for a VIT Chain account."""
    try:
        account = await db.scalar(select(ChainAccount).where(ChainAccount.address == address))
        if not account:
            raise HTTPException(status_code=404, detail=f"Address {address} not found")
        return {
            "address": account.address,
            "balance": str(account.balance or 0),
            "staked": str(account.staked or 0),
            "nonce": account.nonce or 0,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch account: {str(exc)}") from exc

@router.get("/api/supply")
async def get_supply(db: AsyncSession = Depends(get_db)):
    """Canonical supply snapshot derived from chain account balances."""
    try:
        total_supply = await db.scalar(select(func.sum(ChainAccount.balance))) or 0
        staked_supply = await db.scalar(select(func.sum(ChainAccount.staked))) or 0
        total_accounts = await db.scalar(select(func.count(ChainAccount.address))) or 0
        return {
            "max_supply": "1000000000",
            "total_supply": str(total_supply),
            "circulating_supply": str(total_supply),
            "staked_supply": str(staked_supply),
            "locked_supply": "0",
            "treasury_supply": "0",
            "burned_supply": "0",
            "issued_supply": str(total_supply),
            "total_accounts": total_accounts,
            "updated_at": int(time.time()),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch supply: {str(exc)}") from exc

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
