# app/modules/wallet/admin_routes.py
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.deps import get_current_user
from app.modules.wallet.models import (
    WithdrawalRequest, Wallet, WalletTransaction,
    WalletSubscriptionPlan, PlatformConfig,
)

router = APIRouter(prefix="/api/admin/wallet", tags=["Admin Wallet"])


def _require_admin(user):
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")


# ── Withdrawals ────────────────────────────────────────────────────────

@router.get("/withdrawals")
async def list_withdrawals(
    status: str = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_admin(user)
    query = select(WithdrawalRequest)
    if status:
        query = query.where(WithdrawalRequest.status == status)
    result = await db.execute(query.order_by(WithdrawalRequest.requested_at.desc()))
    rows = result.scalars().all()
    return [
        {
            "id": r.id, "user_id": r.user_id, "currency": r.currency,
            "amount": float(r.amount), "net_amount": float(r.net_amount),
            "status": r.status, "destination": r.destination,
            "requested_at": r.requested_at.isoformat(),
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
        }
        for r in rows
    ]


@router.post("/withdrawals/{request_id}/approve")
async def approve_withdrawal(
    request_id: str,
    note: str = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_admin(user)
    result = await db.execute(select(WithdrawalRequest).where(WithdrawalRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(404, "Request not found")
    if req.status not in ("pending", "manual_review"):
        raise HTTPException(400, "Already processed")
    req.status = "processed"
    req.reviewed_by = user.id
    req.review_note = note
    req.processed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "processed"}


@router.post("/withdrawals/{request_id}/reject")
async def reject_withdrawal(
    request_id: str,
    note: str = "",
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_admin(user)
    result = await db.execute(select(WithdrawalRequest).where(WithdrawalRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(404, "Request not found")
    if req.status not in ("pending", "manual_review"):
        raise HTTPException(400, "Already processed")
    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == req.user_id))
    wallet = wallet_result.scalar_one_or_none()
    if wallet:
        field = f"{req.currency.lower()}_balance"
        setattr(wallet, field, getattr(wallet, field) + req.amount)
    req.status = "rejected"
    req.reviewed_by = user.id
    req.review_note = note
    await db.commit()
    return {"status": "rejected"}


# ── Platform Config ────────────────────────────────────────────────────

@router.get("/config")
async def get_config(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _require_admin(user)
    result = await db.execute(select(PlatformConfig))
    return {c.key: c.value for c in result.scalars().all()}


@router.patch("/config")
async def update_config(
    key: str,
    value: dict,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_admin(user)
    result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == key))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "Config key not found")
    config.value = value
    config.updated_by = user.id
    await db.commit()
    return {"status": "updated", "key": key}


# ── Subscription Plans ─────────────────────────────────────────────────

@router.get("/plans")
async def list_plans(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _require_admin(user)
    result = await db.execute(select(WalletSubscriptionPlan))
    plans = result.scalars().all()
    return [
        {
            "id": p.id, "name": p.name, "description": p.description,
            "price_ngn": float(p.price_ngn), "price_usd": float(p.price_usd),
            "price_usdt": float(p.price_usdt), "price_pi": float(p.price_pi),
            "price_vitcoin": float(p.price_vitcoin),
            "duration_days": p.duration_days, "is_active": p.is_active,
        }
        for p in plans
    ]


@router.post("/plans")
async def create_plan(
    name: str,
    price_ngn: float,
    price_usd: float,
    duration_days: int = 30,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_admin(user)
    plan = WalletSubscriptionPlan(
        name=name, price_ngn=Decimal(str(price_ngn)),
        price_usd=Decimal(str(price_usd)), duration_days=duration_days,
    )
    db.add(plan)
    await db.commit()
    return {"status": "created", "plan": plan.name}


@router.patch("/plans/{plan_id}")
async def update_plan(
    plan_id: str,
    price_ngn: float = None,
    price_usd: float = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_admin(user)
    result = await db.execute(select(WalletSubscriptionPlan).where(WalletSubscriptionPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Plan not found")
    if price_ngn is not None:
        plan.price_ngn = Decimal(str(price_ngn))
    if price_usd is not None:
        plan.price_usd = Decimal(str(price_usd))
    if is_active is not None:
        plan.is_active = is_active
    await db.commit()
    return {"status": "updated"}


# ── Overview ───────────────────────────────────────────────────────────

@router.get("/overview")
async def wallet_overview(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _require_admin(user)
    totals = await db.execute(
        select(func.sum(Wallet.ngn_balance), func.sum(Wallet.usd_balance), func.sum(Wallet.vitcoin_balance))
    )
    t = totals.first()
    tx_count = (await db.execute(select(func.count(WalletTransaction.id)))).scalar()
    pending = (await db.execute(
        select(func.count(WithdrawalRequest.id)).where(WithdrawalRequest.status == "pending")
    )).scalar()
    return {
        "total_balances": {"NGN": float(t[0] or 0), "USD": float(t[1] or 0), "VITCoin": float(t[2] or 0)},
        "total_transactions": tx_count,
        "pending_withdrawals": pending,
    }
