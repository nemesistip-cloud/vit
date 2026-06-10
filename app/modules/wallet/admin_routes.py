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

    # ── Execute real payout via Paystack / Stripe ────────────────────────
    payout_ref = None
    payout_error = None
    try:
        from app.config import PAYSTACK_SECRET_KEY, STRIPE_SECRET_KEY
        import httpx as _httpx
        currency = (req.currency or "NGN").upper()
        if currency in ("NGN", "GHS", "KES", "UGX", "TZS") and PAYSTACK_SECRET_KEY:
            # Paystack Transfer
            amount_subunit = int(float(req.net_amount) * 100)
            async with _httpx.AsyncClient(timeout=15) as _c:
                resp = await _c.post(
                    "https://api.paystack.co/transfer",
                    headers={"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"},
                    json={
                        "source": "balance",
                        "amount": amount_subunit,
                        "recipient": req.destination,
                        "reference": f"WD-{req.id}",
                        "reason": f"VIT withdrawal #{req.id}",
                        "currency": currency,
                    },
                )
            if resp.status_code in (200, 201):
                payout_ref = resp.json().get("data", {}).get("transfer_code", f"WD-{req.id}")
            else:
                payout_error = f"Paystack transfer error {resp.status_code}: {resp.text[:120]}"
        elif currency == "USD" and STRIPE_SECRET_KEY:
            # Stripe Payout — requires connected account
            amount_cents = int(float(req.net_amount) * 100)
            async with _httpx.AsyncClient(timeout=15) as _c:
                resp = await _c.post(
                    "https://api.stripe.com/v1/payouts",
                    auth=(STRIPE_SECRET_KEY, ""),
                    data={
                        "amount": str(amount_cents),
                        "currency": "usd",
                        "description": f"VIT withdrawal #{req.id}",
                        "metadata[withdrawal_id]": req.id,
                    },
                )
            if resp.status_code == 200:
                payout_ref = resp.json().get("id", f"WD-{req.id}")
            else:
                payout_error = f"Stripe payout error {resp.status_code}: {resp.text[:120]}"
    except Exception as _pe:
        payout_error = str(_pe)[:200]

    req.status = "processed"
    req.reviewed_by = user.id
    req.review_note = (note or "") + (f" | payout_ref={payout_ref}" if payout_ref else "") + (f" | payout_error={payout_error}" if payout_error else "")
    req.processed_at = datetime.now(timezone.utc)
    await db.commit()

    # Notify user
    try:
        from app.modules.notifications.service import NotificationService as _NS
        from app.modules.notifications.models import NotificationType as _NT, NotificationChannel as _NC
        await _NS.create(db=db, user_id=req.user_id, type=_NT.WALLET_ACTIVITY,
            context={"action": "Withdrawal processed", "amount": float(req.net_amount), "currency": req.currency},
            title="Withdrawal Approved",
            body=f"Your withdrawal of {float(req.net_amount):.2f} {req.currency} has been approved and processed.",
            channel=_NC.IN_APP)
        await db.commit()
    except Exception:
        pass

    return {"status": "processed", "payout_ref": payout_ref, "payout_error": payout_error}


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
    # ── Refund reserved funds back to wallet ─────────────────────────────
    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == req.user_id))
    wallet = wallet_result.scalar_one_or_none()
    if wallet:
        field = f"{req.currency.lower()}_balance"
        current = getattr(wallet, field, Decimal("0")) or Decimal("0")
        setattr(wallet, field, current + req.amount)
        # Record reversal transaction for audit
        from app.modules.wallet.models import WalletTransaction
        reversal_tx = WalletTransaction(
            user_id=req.user_id,
            wallet_id=wallet.id,
            type="withdrawal",
            currency=req.currency,
            amount=req.amount,
            direction="credit",
            status="confirmed",
            reference=f"rejection-refund:{req.id}",
            tx_metadata={"reason": "withdrawal_rejected", "request_id": req.id, "review_note": note or ""},
            processed_at=datetime.now(timezone.utc),
        )
        db.add(reversal_tx)
    req.status = "rejected"
    req.reviewed_by = user.id
    req.review_note = note
    await db.commit()

    # Notify user
    try:
        from app.modules.notifications.service import NotificationService as _NS
        from app.modules.notifications.models import NotificationType as _NT, NotificationChannel as _NC
        await _NS.create(db=db, user_id=req.user_id, type=_NT.WALLET_ACTIVITY,
            context={"action": "Withdrawal rejected", "amount": float(req.amount), "currency": req.currency},
            title="Withdrawal Rejected",
            body=f"Your withdrawal request of {float(req.amount):.2f} {req.currency} was rejected. Funds have been returned to your wallet.",
            channel=_NC.IN_APP)
        await db.commit()
    except Exception:
        pass

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
