# app/modules/bridge/routes.py
"""Cross-Chain Bridge REST API — Module J."""

import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.db.database import get_db
from app.db.models import User
from app.modules.bridge import service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bridge", tags=["bridge"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class BridgeInitiate(BaseModel):
    pool_id:             int
    amount_in:           Decimal   = Field(..., gt=0)
    destination_address: str      = Field(..., min_length=10, max_length=255)
    source_address:      Optional[str] = None


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


# ── Public/User endpoints ──────────────────────────────────────────────────────

@router.get("/pools", summary="List active bridge pools")
async def list_pools(
    db: AsyncSession = Depends(get_db),
    _: User          = Depends(get_current_user),
):
    await svc.seed_default_pools(db)
    pools = await svc.list_pools(db)
    return [_fmt_pool(p) for p in pools]


@router.get("/pools/{pool_id}", summary="Get bridge pool details")
async def get_pool(
    pool_id: int,
    db:      AsyncSession = Depends(get_db),
    _:       User         = Depends(get_current_user),
):
    pool = await svc.get_pool(db, pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    return _fmt_pool(pool)


@router.post("/initiate", summary="Initiate a cross-chain bridge transfer", status_code=201)
async def initiate_bridge(
    body:         BridgeInitiate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
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


@router.get("/transactions/my", summary="My bridge transaction history")
async def my_transactions(
    limit:  int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db:     AsyncSession = Depends(get_db),
    current_user: User   = Depends(get_current_user),
):
    txs = await svc.my_transactions(db, current_user.id, limit=limit, offset=offset)
    return [_fmt_tx(t) for t in txs]


@router.get("/transactions/{tx_id}", summary="Get a specific bridge transaction")
async def get_transaction(
    tx_id: int,
    db:    AsyncSession = Depends(get_db),
    current_user: User  = Depends(get_current_user),
):
    tx = await svc.get_transaction(db, tx_id)
    if not tx or tx.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _fmt_tx(tx)


@router.get("/stats", summary="Bridge platform statistics")
async def bridge_stats(
    db: AsyncSession = Depends(get_db),
    _:  User         = Depends(get_current_user),
):
    return await svc.bridge_stats(db)


# ── Relayer endpoint (admin-protected) ────────────────────────────────────────

@router.post("/relayer/confirm", summary="Relayer: confirm cross-chain transfer")
async def relayer_confirm(
    body: RelayerConfirm,
    db:   AsyncSession = Depends(get_db),
    _:    User         = Depends(get_current_admin),
):
    try:
        tx = await svc.confirm_bridge(db, body.tx_hash, body.relayer_tx_hash, actor="relayer")
        return _fmt_tx(tx)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/transactions", summary="Admin: all bridge transactions")
async def admin_all_transactions(
    status: Optional[str] = None,
    limit:  int = Query(default=100, ge=1, le=500),
    db:     AsyncSession = Depends(get_db),
    _:      User         = Depends(get_current_admin),
):
    from sqlalchemy import select
    from app.modules.bridge.models import BridgeTransaction
    q = select(BridgeTransaction)
    if status:
        q = q.where(BridgeTransaction.status == status)
    q = q.order_by(BridgeTransaction.created_at.desc()).limit(limit)
    result = await db.execute(q)
    txs = result.scalars().all()
    return [_fmt_tx(t) for t in txs]
