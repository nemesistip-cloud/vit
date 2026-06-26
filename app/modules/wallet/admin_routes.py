"""app/modules/wallet/admin_routes.py — Wallet admin routes (full rebuild).

All routes: prefix /api/admin/wallet
Auth: Depends(require_admin) on every route.
Depends(require_super_admin) on price override.
Every mutation calls await write_audit(...).
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.admin import require_admin, require_super_admin
from app.core.errors import AppError
from app.db.database import get_db
from app.db.models import User
from app.modules.wallet.models import (
    Wallet, WalletTransaction, WithdrawalRequest,
    VITCoinPriceHistory, PlatformConfig,
    TransactionType, TransactionDirection, TransactionStatus, Currency,
)
from app.services.audit import write_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/wallet", tags=["Admin Wallet"])


# ── Transactions ───────────────────────────────────────────────────────────────

@router.get("/transactions")
async def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[int] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    currency: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = select(WalletTransaction)
    if user_id:
        q = q.where(WalletTransaction.user_id == user_id)
    if type:
        q = q.where(WalletTransaction.transaction_type == type)
    if status:
        q = q.where(WalletTransaction.status == status)
    if currency:
        q = q.where(WalletTransaction.currency == currency)
    if date_from:
        q = q.where(WalletTransaction.created_at >= date_from)
    if date_to:
        q = q.where(WalletTransaction.created_at <= date_to)

    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar_one()

    q = q.order_by(desc(WalletTransaction.created_at)).offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    txs = result.scalars().all()

    def fmt(t: WalletTransaction) -> dict:
        return {
            "id": t.id, "user_id": t.user_id,
            "type": str(t.transaction_type.value) if hasattr(t.transaction_type, "value") else str(t.transaction_type),
            "direction": str(t.direction.value) if hasattr(t, "direction") and hasattr(t.direction, "value") else getattr(t, "direction", None),
            "amount": float(t.amount or 0),
            "currency": str(t.currency.value) if hasattr(t.currency, "value") else str(t.currency),
            "status": str(t.status.value) if hasattr(t.status, "value") else str(t.status),
            "description": getattr(t, "description", None),
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }

    return {"total": total, "page": page, "limit": limit, "transactions": [fmt(t) for t in txs]}


class ManualCreditBody(BaseModel):
    user_id: int
    amount: float
    currency: str = "VIT"
    reason: str


@router.post("/manual-credit")
async def manual_credit(
    body: ManualCreditBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == body.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise AppError("User not found", status_code=404, code="not_found")

    wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == body.user_id))
    wallet = wallet_res.scalar_one_or_none()
    if not wallet:
        raise AppError("Wallet not found", status_code=404, code="not_found")

    before_balance = float(wallet.vitcoin_balance or 0)
    wallet.vitcoin_balance = Decimal(str(before_balance)) + Decimal(str(body.amount))

    tx = WalletTransaction(
        id=str(uuid.uuid4()),
        user_id=body.user_id,
        wallet_id=wallet.id,
        transaction_type=TransactionType.admin_credit,
        direction=TransactionDirection.credit,
        amount=Decimal(str(body.amount)),
        currency=Currency.VIT,
        status=TransactionStatus.completed,
        description=f"Admin credit: {body.reason}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(tx)
    await db.commit()
    await write_audit(
        db, admin.id, "wallet.manual_credit", "user", body.user_id,
        {"balance": before_balance},
        {"balance": float(wallet.vitcoin_balance), "credited": body.amount, "reason": body.reason},
        request,
    )
    return {"ok": True, "new_balance": float(wallet.vitcoin_balance)}


class ManualDebitBody(BaseModel):
    user_id: int
    amount: float
    currency: str = "VIT"
    reason: str


@router.post("/manual-debit")
async def manual_debit(
    body: ManualDebitBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == body.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise AppError("User not found", status_code=404, code="not_found")

    wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == body.user_id))
    wallet = wallet_res.scalar_one_or_none()
    if not wallet:
        raise AppError("Wallet not found", status_code=404, code="not_found")

    before_balance = float(wallet.vitcoin_balance or 0)
    if before_balance < body.amount:
        raise AppError("Insufficient balance", status_code=400, code="insufficient_balance",
                       details={"available": before_balance, "requested": body.amount})

    wallet.vitcoin_balance = Decimal(str(before_balance)) - Decimal(str(body.amount))

    tx = WalletTransaction(
        id=str(uuid.uuid4()),
        user_id=body.user_id,
        wallet_id=wallet.id,
        transaction_type=TransactionType.admin_debit,
        direction=TransactionDirection.debit,
        amount=Decimal(str(body.amount)),
        currency=Currency.VIT,
        status=TransactionStatus.completed,
        description=f"Admin debit: {body.reason}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(tx)
    await db.commit()
    await write_audit(
        db, admin.id, "wallet.manual_debit", "user", body.user_id,
        {"balance": before_balance},
        {"balance": float(wallet.vitcoin_balance), "debited": body.amount, "reason": body.reason},
        request,
    )
    return {"ok": True, "new_balance": float(wallet.vitcoin_balance)}


# ── VITCoin Price ──────────────────────────────────────────────────────────────

@router.get("/vitcoin-price")
async def get_vitcoin_price(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(
        select(VITCoinPriceHistory).order_by(desc(VITCoinPriceHistory.calculated_at)).limit(1)
    )
    current = result.scalar_one_or_none()

    history_res = await db.execute(
        select(VITCoinPriceHistory).order_by(desc(VITCoinPriceHistory.calculated_at)).limit(30)
    )
    history = history_res.scalars().all()

    total_supply_res = await db.execute(select(func.sum(Wallet.vitcoin_balance)))
    circulating = float(total_supply_res.scalar_one() or 0)

    return {
        "current_price_usd": float(current.price_usd) if current else 0.10,
        "circulating_supply": circulating,
        "history": [
            {
                "price_usd": float(h.price_usd),
                "calculated_at": h.calculated_at.isoformat() if h.calculated_at else None,
            }
            for h in reversed(history)
        ],
    }


class PriceOverrideBody(BaseModel):
    price_usd: float


@router.post("/vitcoin-price/override")
async def override_vitcoin_price(
    body: PriceOverrideBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    if body.price_usd <= 0:
        raise AppError("Price must be positive", status_code=400, code="invalid_input")

    supply_res = await db.execute(select(func.sum(Wallet.vitcoin_balance)))
    supply = float(supply_res.scalar_one() or 0)

    entry = VITCoinPriceHistory(
        id=str(uuid.uuid4()),
        price_usd=Decimal(str(body.price_usd)),
        circulating_supply=Decimal(str(supply)),
        calculated_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.commit()
    await write_audit(db, admin.id, "vitcoin.price_override", "vitcoin_price", None,
                      None, {"price_usd": body.price_usd}, request)
    return {"ok": True, "price_usd": body.price_usd}


# ── Revenue ────────────────────────────────────────────────────────────────────

@router.get("/platform-revenue")
async def platform_revenue(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    total_res = await db.execute(
        select(WalletTransaction.currency, func.sum(WalletTransaction.amount))
        .where(WalletTransaction.transaction_type.in_(["fee", "platform_fee", "subscription"]))
        .group_by(WalletTransaction.currency)
    )
    by_currency = {str(row[0].value if hasattr(row[0], "value") else row[0]): float(row[1] or 0)
                   for row in total_res.all()}

    trend_res = await db.execute(
        select(func.sum(WalletTransaction.amount))
        .where(
            WalletTransaction.transaction_type.in_(["fee", "platform_fee", "subscription"]),
            WalletTransaction.created_at >= thirty_days_ago,
        )
    )
    revenue_30d = float(trend_res.scalar_one() or 0)

    return {
        "by_currency": by_currency,
        "revenue_30d": revenue_30d,
    }


# ── Withdrawal Queue ───────────────────────────────────────────────────────────

@router.get("/withdrawal-queue")
async def withdrawal_queue(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.status == "pending")
        .order_by(WithdrawalRequest.requested_at)
    )
    rows = result.scalars().all()

    out = []
    for r in rows:
        user_res = await db.execute(select(User).where(User.id == r.user_id))
        u = user_res.scalar_one_or_none()
        out.append({
            "id": r.id, "user_id": r.user_id,
            "username": u.username if u else None,
            "email": u.email if u else None,
            "kyc_status": getattr(u, "kyc_status", "unverified") if u else None,
            "currency": str(r.currency.value) if hasattr(r.currency, "value") else str(r.currency),
            "amount": float(r.amount),
            "net_amount": float(r.net_amount),
            "destination": r.destination,
            "requested_at": r.requested_at.isoformat() if r.requested_at else None,
        })
    return out


@router.post("/withdrawal/{tx_id}/approve")
async def approve_withdrawal(
    tx_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(WithdrawalRequest).where(WithdrawalRequest.id == tx_id))
    req = result.scalar_one_or_none()
    if not req:
        raise AppError("Withdrawal not found", status_code=404, code="not_found")
    if req.status != "pending":
        raise AppError(f"Withdrawal is already {req.status}", status_code=400, code="invalid_state")

    before = {"status": req.status}
    req.status = "approved"
    req.processed_at = datetime.now(timezone.utc)
    await db.commit()
    await write_audit(db, admin.id, "withdrawal.approve", "withdrawal", tx_id,
                      before, {"status": "approved"}, request)
    return {"ok": True, "status": "approved"}


class RejectWithdrawalBody(BaseModel):
    reason: str


@router.post("/withdrawal/{tx_id}/reject")
async def reject_withdrawal(
    tx_id: str,
    body: RejectWithdrawalBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(WithdrawalRequest).where(WithdrawalRequest.id == tx_id))
    req = result.scalar_one_or_none()
    if not req:
        raise AppError("Withdrawal not found", status_code=404, code="not_found")
    if req.status != "pending":
        raise AppError(f"Withdrawal is already {req.status}", status_code=400, code="invalid_state")

    before = {"status": req.status}
    req.status = "rejected"
    req.rejection_reason = body.reason
    req.processed_at = datetime.now(timezone.utc)

    wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == req.user_id))
    wallet = wallet_res.scalar_one_or_none()
    if wallet:
        wallet.vitcoin_balance = (wallet.vitcoin_balance or Decimal("0")) + (req.amount or Decimal("0"))

    await db.commit()
    await write_audit(db, admin.id, "withdrawal.reject", "withdrawal", tx_id,
                      before, {"status": "rejected", "reason": body.reason}, request)
    return {"ok": True, "status": "rejected"}
