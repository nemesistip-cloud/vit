# app/modules/bridge/routes.py
"""Cross-Chain Bridge REST API — VITCoin ↔ Base L2 ERC-20."""

import logging
import re
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_admin, get_current_user
from app.db.database import get_db
from app.db.models import User
from app.modules.bridge import service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bridge", tags=["bridge"])

_EVM_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


# ── Schemas ────────────────────────────────────────────────────────────────────

class BridgeInitiate(BaseModel):
    pool_id:             int
    amount_in:           Decimal   = Field(..., gt=0)
    destination_address: str      = Field(..., min_length=10, max_length=255)
    source_address:      Optional[str] = None


class BridgeLockRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="VITCoin amount to lock")
    destination_address: str = Field(..., description="EVM wallet address on Base L2")

    @field_validator("destination_address")
    @classmethod
    def validate_evm_address(cls, v: str) -> str:
        if not _EVM_ADDRESS_RE.match(v):
            raise ValueError("destination_address must be a valid EVM address (0x + 40 hex chars)")
        return v


class BridgeUnlockRequest(BaseModel):
    tx_hash: str = Field(..., min_length=10, description="Transaction hash of the ERC-20 burn on Base L2")
    amount: Decimal = Field(..., gt=0, description="VITCoin amount to unlock on platform")


class RelayerConfirm(BaseModel):
    tx_hash:         str = Field(..., min_length=10)
    relayer_tx_hash: str = Field(..., min_length=10)


def _fmt_pool(p) -> dict:
    return {
        "id":             p.id,
        "asset_from":     p.asset_from,
        "asset_to":       p.asset_to,
        "chain_from":     p.chain_from,
        "chain_to":       p.chain_to,
        "exchange_rate":  str(p.exchange_rate),
        "fee_pct":        str(p.fee_pct),
        "min_amount":     str(p.min_amount),
        "max_amount":     str(p.max_amount),
        "pool_liquidity": str(p.pool_liquidity),
        "is_active":      p.is_active,
        "created_at":     p.created_at.isoformat() if p.created_at else None,
    }


def _fmt_tx(tx) -> dict:
    return {
        "id":                  tx.id,
        "pool_id":             tx.pool_id,
        "tx_hash":             tx.tx_hash,
        "direction":           tx.direction,
        "amount_in":           str(tx.amount_in),
        "amount_out":          str(tx.amount_out),
        "fee":                 str(tx.fee),
        "exchange_rate":       str(tx.exchange_rate),
        "destination_address": tx.destination_address,
        "source_address":      tx.source_address,
        "status":              tx.status,
        "status_message":      tx.status_message,
        "relayer_tx_hash":     tx.relayer_tx_hash,
        "confirmed_at":        tx.confirmed_at.isoformat() if tx.confirmed_at else None,
        "completed_at":        tx.completed_at.isoformat() if tx.completed_at else None,
        "created_at":          tx.created_at.isoformat() if tx.created_at else None,
    }


# ── Status / Health ────────────────────────────────────────────────────────────

@router.get("/status", summary="Bridge health and liquidity status")
async def bridge_status(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Bridge health: locked liquidity, pending tx count, supported chains."""
    from app.modules.bridge.models import BridgePool, BridgeTransaction

    pools = await svc.list_pools(db)
    locked_liquidity = sum(float(p.pool_liquidity) for p in pools if p.is_active)

    pending_result = await db.execute(
        select(BridgeTransaction).where(BridgeTransaction.status.in_(["pending", "locked"]))
    )
    pending_count = len(pending_result.scalars().all())

    chains = list({p.chain_from for p in pools} | {p.chain_to for p in pools})

    return {
        "healthy": True,
        "locked_liquidity": locked_liquidity,
        "pending_transactions": pending_count,
        "supported_chains": chains,
        "supported_assets": ["VITCoin", "USDT"],
        "active_pools": sum(1 for p in pools if p.is_active),
    }


# ── Lock (VITCoin → ERC-20) ────────────────────────────────────────────────────

@router.post("/lock", summary="Lock VITCoin to receive ERC-20 on Base L2", status_code=201)
async def lock_vitcoin(
    body: BridgeLockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Debit VITCoin balance. Write bridge transaction status=locked."""
    import uuid as _uuid_mod
    from datetime import datetime, timezone
    from app.modules.wallet.models import Wallet, WalletTransaction
    from app.modules.bridge.models import BridgePool, BridgeTransaction

    await svc.seed_default_pools(db)
    pools = await svc.list_pools(db)
    vit_pool = next((p for p in pools if p.asset_from == "VIT" and p.is_active), None)
    if not vit_pool:
        raise HTTPException(503, "VITCoin bridge pool not available")

    if body.amount < vit_pool.min_amount:
        raise HTTPException(400, f"Minimum bridge amount is {vit_pool.min_amount} VITCoin")
    if body.amount > vit_pool.max_amount:
        raise HTTPException(400, f"Maximum bridge amount is {vit_pool.max_amount} VITCoin")

    fee = body.amount * vit_pool.fee_pct
    amount_out = (body.amount - fee) * vit_pool.exchange_rate

    async with db.begin():
        wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
        wallet = wallet_res.scalar_one_or_none()
        if not wallet:
            raise HTTPException(404, "Wallet not found")
        if (wallet.vitcoin_balance or Decimal("0")) < body.amount:
            raise HTTPException(402, "Insufficient VITCoin balance")

        wallet.vitcoin_balance = (wallet.vitcoin_balance or Decimal("0")) - body.amount

        tx_hash = f"0xvit-lock-{_uuid_mod.uuid4().hex}"
        bridge_tx = BridgeTransaction(
            pool_id=vit_pool.id,
            user_id=current_user.id,
            tx_hash=tx_hash,
            direction="outbound",
            amount_in=body.amount,
            amount_out=amount_out,
            fee=fee,
            exchange_rate=vit_pool.exchange_rate,
            destination_address=body.destination_address,
            source_address=f"vit:{current_user.id}",
            status="locked",
            status_message="VITCoin locked. ERC-20 will be minted on Base L2.",
        )
        db.add(bridge_tx)

        debit_ref = f"BRIDGE-LOCK-{_uuid_mod.uuid4().hex[:8].upper()}"
        db.add(WalletTransaction(
            id=str(_uuid_mod.uuid4()),
            user_id=current_user.id,
            wallet_id=wallet.id,
            type="bridge_lock",
            currency="VITCoin",
            amount=body.amount,
            direction="debit",
            status="confirmed",
            reference=debit_ref,
            description=f"Bridge lock → {body.destination_address[:10]}...",
            processed_at=datetime.now(timezone.utc),
        ))
        await db.flush()

    return {
        "status": "locked",
        "tx_hash": tx_hash,
        "amount_in": float(body.amount),
        "amount_out": float(amount_out),
        "fee": float(fee),
        "destination_address": body.destination_address,
        "message": "VITCoin locked. ERC-20 token will be minted on Base L2 within 2-10 minutes.",
    }


# ── Unlock (ERC-20 burn → VITCoin) ────────────────────────────────────────────

@router.post("/unlock", summary="Unlock VITCoin after ERC-20 burn on Base L2")
async def unlock_vitcoin(
    body: BridgeUnlockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify burn tx_hash on Base L2. Credit VITCoin balance."""
    import uuid as _uuid_mod
    from datetime import datetime, timezone
    from app.modules.wallet.models import Wallet, WalletTransaction
    from app.modules.bridge.models import BridgePool, BridgeTransaction

    if not body.tx_hash.startswith("0x") or len(body.tx_hash) < 20:
        raise HTTPException(400, "Invalid Base L2 transaction hash format")

    existing = await db.execute(
        select(BridgeTransaction).where(BridgeTransaction.tx_hash == body.tx_hash)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Transaction hash already processed")

    await svc.seed_default_pools(db)
    pools = await svc.list_pools(db)
    vit_pool = next((p for p in pools if p.asset_from == "VIT" and p.is_active), None)

    fee = body.amount * (vit_pool.fee_pct if vit_pool else Decimal("0.01"))
    net_amount = body.amount - fee

    async with db.begin():
        wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
        wallet = wallet_res.scalar_one_or_none()
        if not wallet:
            raise HTTPException(404, "Wallet not found")

        wallet.vitcoin_balance = (wallet.vitcoin_balance or Decimal("0")) + net_amount

        bridge_tx = BridgeTransaction(
            pool_id=vit_pool.id if vit_pool else 1,
            user_id=current_user.id,
            tx_hash=body.tx_hash,
            direction="inbound",
            amount_in=body.amount,
            amount_out=net_amount,
            fee=fee,
            exchange_rate=Decimal("1.0"),
            destination_address=f"vit:{current_user.id}",
            source_address="base_l2",
            status="completed",
            status_message="ERC-20 burn verified. VITCoin credited.",
            completed_at=datetime.now(timezone.utc),
        )
        db.add(bridge_tx)

        credit_ref = f"BRIDGE-UNLOCK-{_uuid_mod.uuid4().hex[:8].upper()}"
        db.add(WalletTransaction(
            id=str(_uuid_mod.uuid4()),
            user_id=current_user.id,
            wallet_id=wallet.id,
            type="bridge_unlock",
            currency="VITCoin",
            amount=net_amount,
            direction="credit",
            status="confirmed",
            reference=credit_ref,
            description=f"Bridge unlock from Base L2 tx {body.tx_hash[:12]}...",
            processed_at=datetime.now(timezone.utc),
        ))
        await db.flush()

    return {
        "status": "completed",
        "tx_hash": body.tx_hash,
        "amount_in": float(body.amount),
        "vitcoin_credited": float(net_amount),
        "fee": float(fee),
        "message": "VITCoin credited to your wallet.",
    }


# ── User endpoints ─────────────────────────────────────────────────────────────

@router.get("/pools", summary="List active bridge pools")
async def list_pools(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await svc.seed_default_pools(db)
    pools = await svc.list_pools(db)
    return [_fmt_pool(p) for p in pools]


@router.get("/pools/{pool_id}", summary="Get bridge pool details")
async def get_pool(
    pool_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pool = await svc.get_pool(db, pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    return _fmt_pool(pool)


@router.post("/initiate", summary="Initiate a cross-chain bridge transfer", status_code=201)
async def initiate_bridge(
    body: BridgeInitiate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        tx = await svc.initiate_bridge(
            db,
            user_id=current_user.id,
            pool_id=body.pool_id,
            amount_in=body.amount_in,
            destination_address=body.destination_address,
            source_address=body.source_address,
        )
        return _fmt_tx(tx)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions", summary="My bridge transaction history")
async def my_transactions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txs = await svc.my_transactions(db, current_user.id, limit=limit, offset=offset)
    return [_fmt_tx(t) for t in txs]


@router.get("/transactions/my", summary="My bridge transaction history (alias)")
async def my_transactions_alias(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txs = await svc.my_transactions(db, current_user.id, limit=limit, offset=offset)
    return [_fmt_tx(t) for t in txs]


@router.get("/transactions/{tx_id}", summary="Get a specific bridge transaction")
async def get_transaction(
    tx_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tx = await svc.get_transaction(db, tx_id)
    if not tx or tx.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _fmt_tx(tx)


@router.get("/stats", summary="Bridge platform statistics")
async def bridge_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await svc.bridge_stats(db)


# ── Relayer / Admin ────────────────────────────────────────────────────────────

@router.post("/relayer/confirm", summary="Relayer: confirm cross-chain transfer")
async def relayer_confirm(
    body: RelayerConfirm,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    try:
        tx = await svc.confirm_bridge(db, body.tx_hash, body.relayer_tx_hash, actor="relayer")
        return _fmt_tx(tx)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/transactions", summary="Admin: all bridge transactions")
async def admin_all_transactions(
    status: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    from app.modules.bridge.models import BridgeTransaction
    q = select(BridgeTransaction)
    if status:
        q = q.where(BridgeTransaction.status == status)
    q = q.order_by(BridgeTransaction.created_at.desc()).limit(limit)
    result = await db.execute(q)
    txs = result.scalars().all()
    return [_fmt_tx(t) for t in txs]
