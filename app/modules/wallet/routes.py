# app/modules/wallet/routes.py
"""User wallet API endpoints."""

import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.deps import get_current_user
from app.modules.wallet.services import WalletService, WithdrawalService, SubscriptionService
from app.modules.wallet.pricing import VITCoinPricingEngine
from app.modules.wallet.models import (
    Currency, WalletSubscriptionPlan, WalletTransaction, WithdrawalRequest,
    VITCoinPriceHistory, PlatformConfig,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/wallet", tags=["Wallet"])


# ── Request / Response schemas ─────────────────────────────────────────

class DepositInitiateRequest(BaseModel):
    currency: str = Field(..., description="NGN, USD, USDT, PI, VITCoin")
    amount: float = Field(..., gt=0)
    method: str = Field(..., description="paystack, stripe, crypto, pi")


class DepositVerifyRequest(BaseModel):
    reference: str
    currency: str


class ConvertRequest(BaseModel):
    from_currency: str
    to_currency: str
    amount: float = Field(..., gt=0)


class WithdrawRequest(BaseModel):
    currency: str
    amount: float = Field(..., gt=0)
    destination: str
    destination_type: str = Field(..., description="bank_account, usdt_address, pi_wallet, paypal")


class SubscribeRequest(BaseModel):
    plan_id: str
    currency: str


class WalletResponse(BaseModel):
    ngn_balance: float
    usd_balance: float
    usdt_balance: float
    pi_balance: float
    vitcoin_balance: float
    is_frozen: bool
    kyc_verified: bool


# ── Endpoints ──────────────────────────────────────────────────────────

@router.get("/me", response_model=WalletResponse)
async def get_my_wallet(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's wallet balances."""
    service = WalletService(db)
    wallet = await service.get_or_create_wallet(current_user.id)
    return WalletResponse(
        ngn_balance=float(wallet.ngn_balance),
        usd_balance=float(wallet.usd_balance),
        usdt_balance=float(wallet.usdt_balance),
        pi_balance=float(wallet.pi_balance),
        vitcoin_balance=float(wallet.vitcoin_balance),
        is_frozen=wallet.is_frozen,
        kyc_verified=wallet.kyc_verified,
    )


@router.get("/transactions")
async def get_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    transaction_type: Optional[str] = None,
    currency: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated transaction history."""
    service = WalletService(db)
    currency_filter = Currency(currency) if currency else None
    total, transactions = await service.get_transaction_history(
        user_id=current_user.id,
        limit=limit,
        offset=(page - 1) * limit,
        transaction_type=transaction_type,
        currency=currency_filter,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "transactions": [
            {
                "id": t.id,
                "type": t.type,
                "currency": t.currency,
                "amount": float(t.amount),
                "direction": t.direction,
                "status": t.status,
                "reference": t.reference,
                "fee_amount": float(t.fee_amount),
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ],
    }


@router.post("/deposit/initiate")
async def initiate_deposit(
    request: DepositInitiateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a deposit — calls Paystack/Stripe when keys are configured."""
    import uuid as _uuid
    import os as _os

    service = WalletService(db)
    wallet = await service.get_or_create_wallet(current_user.id)
    ref = f"DEP-{current_user.id}-{_uuid.uuid4().hex[:8].upper()}"

    payment_link = None
    gateway_error = None

    # ── Paystack (NGN) ────────────────────────────────────────────────
    if request.method == "paystack":
        paystack_key = _os.environ.get("PAYSTACK_SECRET_KEY", "")
        if paystack_key:
            try:
                import httpx as _httpx
                # Paystack expects amount in kobo (NGN * 100)
                amount_kobo = int(float(request.amount) * 100)
                async with _httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        "https://api.paystack.co/transaction/initialize",
                        headers={"Authorization": f"Bearer {paystack_key}"},
                        json={
                            "email": current_user.email,
                            "amount": amount_kobo,
                            "reference": ref,
                            "currency": "NGN",
                            "metadata": {
                                "user_id": current_user.id,
                                "vit_ref": ref,
                            },
                        },
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status"):
                        payment_link = data["data"]["authorization_url"]
                else:
                    gateway_error = f"Paystack error {resp.status_code}"
            except Exception as _e:
                gateway_error = str(_e)

    # ── Stripe (USD) ──────────────────────────────────────────────────
    elif request.method == "stripe":
        stripe_key = _os.environ.get("STRIPE_SECRET_KEY", "")
        if stripe_key:
            try:
                import httpx as _httpx
                amount_cents = int(float(request.amount) * 100)
                async with _httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        "https://api.stripe.com/v1/checkout/sessions",
                        auth=(stripe_key, ""),
                        data={
                            "payment_method_types[]": "card",
                            "line_items[0][price_data][currency]": "usd",
                            "line_items[0][price_data][product_data][name]": "VIT Wallet Deposit",
                            "line_items[0][price_data][unit_amount]": str(amount_cents),
                            "line_items[0][quantity]": "1",
                            "mode": "payment",
                            "client_reference_id": ref,
                            "success_url": f"https://{_os.environ.get('REPL_SLUG', 'localhost')}.replit.app/wallet?deposit=success&ref={ref}",
                            "cancel_url": f"https://{_os.environ.get('REPL_SLUG', 'localhost')}.replit.app/wallet?deposit=cancelled",
                            "metadata[vit_ref]": ref,
                            "metadata[user_id]": str(current_user.id),
                        },
                    )
                if resp.status_code == 200:
                    payment_link = resp.json().get("url")
                else:
                    gateway_error = f"Stripe error {resp.status_code}"
            except Exception as _e:
                gateway_error = str(_e)

    # ── Record pending transaction ─────────────────────────────────────
    try:
        from app.modules.wallet.models import WalletTransaction as _WalletTx
        pending_tx = _WalletTx(
            id=str(_uuid.uuid4()),
            user_id=current_user.id,
            wallet_id=wallet.id,
            type="deposit",
            currency=request.currency.upper(),
            amount=Decimal(str(request.amount)),
            direction="credit",
            status="pending",
            reference=ref,
            tx_metadata={
                "method": request.method,
                "gateway_error": gateway_error,
                "payment_link": payment_link,
            },
        )
        db.add(pending_tx)
        await db.commit()
        # ── Notification ────────────────────────────────────────────────
        try:
            from app.modules.notifications.service import NotificationService
            from app.modules.notifications.models import NotificationType, NotificationChannel
            await NotificationService.create(
                db, current_user.id,
                NotificationType.WALLET_ACTIVITY,
                {"action": "Deposit initiated", "amount": request.amount, "currency": request.currency.upper()},
                title="Deposit Initiated",
                body=f"Your deposit of {request.amount} {request.currency.upper()} has been initiated. Ref: {ref}",
                channel=NotificationChannel.IN_APP,
            )
            await db.commit()
        except Exception as _notify_err:
            logger.warning(f"Deposit initiation notification failed for user {current_user.id}: {_notify_err}")
    except Exception as _tx_err:
        logger.error(f"Failed to record pending deposit transaction for user {current_user.id}: {_tx_err}")
        await db.rollback()

    fallback_link = payment_link or f"https://paystack.com/pay/vit-sports?ref={ref}"

    return {
        "status": "pending",
        "reference": ref,
        "payment_link": fallback_link,
        "gateway_error": gateway_error,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "currency": request.currency,
        "amount": request.amount,
        "method": request.method,
    }


@router.post("/deposit/verify")
async def verify_deposit(
    request: DepositVerifyRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a completed deposit and credit the wallet if confirmed."""
    import os as _os
    from app.modules.wallet.models import WalletTransaction as _WalletTx, Currency as _Currency

    verified_amount = None
    verified_status = "failed"

    # ── Verify with Paystack ──────────────────────────────────────────
    paystack_key = _os.environ.get("PAYSTACK_SECRET_KEY", "")
    if paystack_key:
        try:
            import httpx as _httpx
            async with _httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://api.paystack.co/transaction/verify/{request.reference}",
                    headers={"Authorization": f"Bearer {paystack_key}"},
                )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") and data["data"]["status"] == "success":
                    verified_amount = Decimal(str(data["data"]["amount"])) / 100  # kobo → NGN
                    verified_status = "confirmed"
        except Exception as _verify_err:
            logger.warning(f"Paystack verification failed for ref {request.reference}: {_verify_err}")

    if verified_status == "confirmed" and verified_amount is not None:
        service = WalletService(db)
        wallet = await service.get_or_create_wallet(current_user.id)
        # Update existing pending tx to confirmed
        tx_result = await db.execute(
            select(_WalletTx).where(
                _WalletTx.reference == request.reference,
                _WalletTx.user_id == current_user.id,
            )
        )
        tx = tx_result.scalar_one_or_none()
        if tx:
            tx.status = "confirmed"
            tx.amount = verified_amount
            tx.processed_at = datetime.now(timezone.utc)
        else:
            import uuid as _uuid
            db.add(_WalletTx(
                id=str(_uuid.uuid4()),
                user_id=current_user.id,
                wallet_id=wallet.id,
                type="deposit",
                currency=request.currency.upper(),
                amount=verified_amount,
                direction="credit",
                status="confirmed",
                reference=request.reference,
            ))
        # Credit the wallet
        try:
            currency_enum = _Currency(request.currency.upper())
        except ValueError:
            currency_enum = _Currency.NGN
        await service.credit(
            wallet_id=wallet.id,
            user_id=current_user.id,
            currency=currency_enum,
            amount=verified_amount,
            tx_type="deposit",
            reference=f"{request.reference}-CREDIT",
        )
        await db.commit()
        # ── Notification ────────────────────────────────────────────────
        try:
            from app.modules.notifications.service import NotificationService as _NS
            from app.modules.notifications.models import NotificationType as _NT, NotificationChannel as _NC
            await _NS.create(
                db, current_user.id,
                _NT.WALLET_ACTIVITY,
                {"action": "Deposit confirmed", "amount": float(verified_amount), "currency": request.currency.upper()},
                title="Deposit Confirmed",
                body=f"Your deposit of {float(verified_amount):.2f} {request.currency.upper()} has been confirmed and credited to your wallet.",
                channel=_NC.IN_APP,
            )
            await db.commit()
        except Exception as _notify_err:
            logger.warning(f"Deposit confirmation notification failed for user {current_user.id}: {_notify_err}")
        return {"status": "confirmed", "amount": float(verified_amount), "currency": request.currency, "reference": request.reference}

    return {"status": verified_status, "reference": request.reference, "currency": request.currency}


@router.post("/kyc/submit")
async def submit_kyc(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit KYC for verification. Sets status to 'pending' — an admin must approve."""
    import logging as _logging
    _log = _logging.getLogger(__name__)

    from app.modules.wallet.models import Wallet as _Wallet
    from app.db.models import User as _User
    from datetime import datetime as _dt

    result = await db.execute(select(_Wallet).where(_Wallet.user_id == current_user.id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(404, "Wallet not found")

    if wallet.kyc_verified:
        return {"kyc_verified": True, "kyc_status": "approved", "message": "KYC already verified."}

    # Set KYC status to pending — admin approval required
    user_res = await db.execute(select(_User).where(_User.id == current_user.id))
    db_user = user_res.scalar_one_or_none()
    if db_user:
        if hasattr(db_user, "kyc_status"):
            current_status = getattr(db_user, "kyc_status", "none")
            if current_status == "pending":
                return {
                    "kyc_verified": False,
                    "kyc_status": "pending",
                    "message": "Your KYC submission is already under review. You will be notified once approved.",
                }
            db_user.kyc_status = "pending"
        if hasattr(db_user, "kyc_submitted_at"):
            db_user.kyc_submitted_at = _dt.now(timezone.utc)

    await db.commit()

    try:
        from app.modules.notifications.service import NotificationService as _NS
        from app.modules.notifications.models import NotificationType as _NT, NotificationChannel as _NC
        await _NS.create(
            db, current_user.id,
            _NT.SYSTEM,
            {"message": "Your KYC submission has been received and is under review."},
            title="KYC Submitted — Under Review",
            body="We have received your KYC submission. You will be notified once an admin completes the review.",
            channel=_NC.IN_APP,
        )
        await db.commit()
    except Exception as _e:
        _log.warning(f"KYC submission notification failed for user {current_user.id}: {_e}")

    return {
        "kyc_verified": False,
        "kyc_status": "pending",
        "message": "KYC submitted successfully. Your identity is under review — you will be notified once approved.",
    }


@router.post("/convert")
async def convert_currency(
    request: ConvertRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert between currencies."""
    try:
        from_cur = Currency(request.from_currency)
        to_cur = Currency(request.to_currency)
    except ValueError:
        raise HTTPException(400, "Invalid currency")

    service = WalletService(db)
    wallet = await service.get_or_create_wallet(current_user.id)

    result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == "conversion_fee_pct"))
    fee_config = result.scalar_one_or_none()
    fee_pct = Decimal(str(fee_config.value.get("value", 1.5))) if fee_config else Decimal("1.5")

    try:
        debit_tx, credit_tx, converted_amount = await service.convert_currency(
            wallet_id=wallet.id,
            user_id=current_user.id,
            from_currency=from_cur,
            to_currency=to_cur,
            amount=Decimal(str(request.amount)),
            conversion_fee_pct=fee_pct,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    await db.commit()
    updated = await service.get_or_create_wallet(current_user.id)
    return {
        "from_currency": request.from_currency,
        "to_currency": request.to_currency,
        "from_amount": request.amount,
        "to_amount": float(converted_amount),
        "fee": float(debit_tx.fee_amount),
        "fee_percent": float(fee_pct),
        "new_balances": {
            "ngn": float(updated.ngn_balance),
            "usd": float(updated.usd_balance),
            "usdt": float(updated.usdt_balance),
            "pi": float(updated.pi_balance),
            "vitcoin": float(updated.vitcoin_balance),
        },
    }


@router.post("/withdraw")
async def withdraw(
    request: WithdrawRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request a withdrawal."""
    try:
        currency = Currency(request.currency)
    except ValueError:
        raise HTTPException(400, "Invalid currency")

    wallet_service = WalletService(db)
    withdrawal_service = WithdrawalService(db, wallet_service)
    wallet = await wallet_service.get_or_create_wallet(current_user.id)

    result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == "auto_withdrawal_limits"))
    limits_config = result.scalar_one_or_none()
    role = getattr(current_user, "role", "viewer")
    if limits_config:
        auto_approve_limit = Decimal(str(limits_config.value.get(role, 0)))
    else:
        auto_approve_limit = Decimal("0")

    try:
        kyc_status = getattr(current_user, "kyc_status", "none") or "none"
        wr = await withdrawal_service.create_withdrawal_request(
            user_id=current_user.id,
            wallet_id=wallet.id,
            currency=currency,
            amount=Decimal(str(request.amount)),
            destination=request.destination,
            destination_type=request.destination_type,
            auto_approve_limit=auto_approve_limit,
            kyc_status=kyc_status,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    await db.commit()
    return {
        "request_id": str(wr.id),
        "status": wr.status,
        "estimated_processing": "24-48 hours" if wr.status == "pending" else "immediate",
        "amount": float(wr.amount),
        "net_amount": float(wr.net_amount),
        "fee": float(wr.fee_amount),
    }


@router.get("/withdraw/status/{request_id}")
async def get_withdrawal_status(
    request_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get status of a withdrawal request."""
    result = await db.execute(
        select(WithdrawalRequest).where(
            WithdrawalRequest.id == request_id,
            WithdrawalRequest.user_id == current_user.id,
        )
    )
    withdrawal = result.scalar_one_or_none()
    if not withdrawal:
        raise HTTPException(404, "Withdrawal request not found")
    return {
        "request_id": str(withdrawal.id),
        "status": withdrawal.status,
        "amount": float(withdrawal.amount),
        "net_amount": float(withdrawal.net_amount),
        "fee": float(withdrawal.fee_amount),
        "requested_at": withdrawal.requested_at.isoformat(),
        "processed_at": withdrawal.processed_at.isoformat() if withdrawal.processed_at else None,
    }


@router.post("/subscribe")
async def subscribe(
    request: SubscribeRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Subscribe to a wallet plan."""
    try:
        currency = Currency(request.currency)
    except ValueError:
        raise HTTPException(400, "Invalid currency")

    result = await db.execute(
        select(WalletSubscriptionPlan).where(
            WalletSubscriptionPlan.id == request.plan_id,
            WalletSubscriptionPlan.is_active == True,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Plan not found or inactive")

    price_map = {
        "NGN": plan.price_ngn, "USD": plan.price_usd,
        "USDT": plan.price_usdt, "PI": plan.price_pi,
        "VITCoin": plan.price_vitcoin,
        "VITCOIN": plan.price_vitcoin,
        "vitcoin": plan.price_vitcoin,
    }
    price = price_map.get(request.currency)
    if not price or price <= 0:
        raise HTTPException(400, "Plan not available in this currency")

    wallet_service = WalletService(db)
    subscription_service = SubscriptionService(db, wallet_service)
    wallet = await wallet_service.get_or_create_wallet(current_user.id)

    try:
        sub_result = await subscription_service.subscribe(
            user_id=current_user.id, wallet_id=wallet.id,
            plan_id=plan.id, currency=currency, price=price,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    await db.commit()
    return {
        "subscription_id": sub_result["subscription_id"],
        "plan_name": plan.name,
        "currency": request.currency,
        "amount": float(price),
        "expires_at": sub_result["expires_at"].isoformat(),
        "auto_renew": True,
    }


@router.get("/plans")
async def list_plans(db: AsyncSession = Depends(get_db)):
    """List all active subscription plans."""
    result = await db.execute(
        select(WalletSubscriptionPlan).where(WalletSubscriptionPlan.is_active == True)
    )
    plans = result.scalars().all()
    return [
        {
            "id": p.id, "name": p.name, "description": p.description,
            "features": p.features,
            "price_ngn": float(p.price_ngn), "price_usd": float(p.price_usd),
            "price_usdt": float(p.price_usdt), "price_pi": float(p.price_pi),
            "price_vitcoin": float(p.price_vitcoin),
            "duration_days": p.duration_days,
        }
        for p in plans
    ]


@router.get("/statement/export")
async def export_statement_csv(
    currency: Optional[str] = Query(None, description="Filter by currency (NGN, USD, USDT, VITCoin)"),
    limit: int = Query(500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Download wallet transaction history as CSV."""
    from app.modules.wallet.models import Wallet as _Wallet
    wallet_res = await db.execute(select(_Wallet).where(_Wallet.user_id == current_user.id))
    wallet = wallet_res.scalar_one_or_none()
    if not wallet:
        raise HTTPException(404, "Wallet not found")

    q = select(WalletTransaction).where(WalletTransaction.wallet_id == wallet.id)
    if currency:
        q = q.where(WalletTransaction.currency == currency.upper())
    q = q.order_by(WalletTransaction.created_at.desc()).limit(limit)
    result = await db.execute(q)
    txns = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "type", "direction", "currency", "amount", "fee", "status", "reference", "description", "created_at"])
    for tx in txns:
        writer.writerow([
            tx.id,
            tx.transaction_type.value if hasattr(tx.transaction_type, "value") else tx.transaction_type,
            tx.direction.value if hasattr(tx.direction, "value") else tx.direction,
            tx.currency.value if hasattr(tx.currency, "value") else tx.currency,
            float(tx.amount),
            float(tx.fee or 0),
            tx.status.value if hasattr(tx.status, "value") else tx.status,
            tx.reference or "",
            tx.description or "",
            tx.created_at.isoformat() if tx.created_at else "",
        ])
    output.seek(0)

    filename = f"vit_statement_{current_user.username}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/exchange-rates")
async def get_exchange_rates(db: AsyncSession = Depends(get_db)):
    """Get current exchange rates for all supported currencies, including live VITCoin price."""
    pricing = VITCoinPricingEngine(db)
    vit_prices = await pricing.get_current_price()
    vit_usd = float(vit_prices.get("usd", 0.10))

    # NGN/USD from a representative platform configuration or latest known rate
    result_ngn = await db.execute(
        select(PlatformConfig).where(PlatformConfig.key == "ngn_usd_rate")
    )
    ngn_row = result_ngn.scalar_one_or_none()
    ngn_usd_rate = float(ngn_row.value) if ngn_row and ngn_row.value else 0.000633
    ngn_rate = round(1.0 / ngn_usd_rate, 2) if ngn_usd_rate > 0 else 1580.0

    return {
        "rates": {
            "NGN": {"rate_to_usd": ngn_usd_rate, "usd_per_unit": ngn_usd_rate, "symbol": "₦", "label": "Nigerian Naira"},
            "USD": {"rate_to_usd": 1.0, "usd_per_unit": 1.0, "symbol": "$", "label": "US Dollar"},
            "USDT": {"rate_to_usd": 1.0, "usd_per_unit": 1.0, "symbol": "₮", "label": "Tether"},
            "PI": {"rate_to_usd": 0.314159, "usd_per_unit": 0.314159, "symbol": "π", "label": "Pi Network"},
            "VITCoin": {"rate_to_usd": vit_usd, "usd_per_unit": vit_usd, "symbol": "VIT", "label": "VITCoin"},
        },
        "ngn_per_usd": ngn_rate,
        "vit_price_usd": vit_usd,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/admin/kyc/approve/{user_id}")
async def admin_approve_kyc(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Admin: approve a pending KYC submission and enable withdrawals for the user."""
    from app.db.models import User as _User
    from app.modules.wallet.models import Wallet as _Wallet

    if getattr(current_user, "role", "viewer") not in ("admin", "superadmin"):
        raise HTTPException(403, "Admin privileges required.")

    user_res = await db.execute(select(_User).where(_User.id == user_id))
    db_user = user_res.scalar_one_or_none()
    if not db_user:
        raise HTTPException(404, "User not found.")

    kyc_status = getattr(db_user, "kyc_status", "none")
    if kyc_status == "approved":
        return {"user_id": user_id, "kyc_status": "approved", "message": "User KYC was already approved."}
    if kyc_status not in ("pending",):
        raise HTTPException(400, f"Cannot approve KYC with status '{kyc_status}'. User must submit KYC first.")

    if hasattr(db_user, "kyc_status"):
        db_user.kyc_status = "approved"

    wallet_res = await db.execute(select(_Wallet).where(_Wallet.user_id == user_id))
    wallet = wallet_res.scalar_one_or_none()
    if wallet:
        wallet.kyc_verified = True

    await db.commit()

    try:
        from app.modules.notifications.service import NotificationService as _NS
        from app.modules.notifications.models import NotificationType as _NT, NotificationChannel as _NC
        await _NS.create(
            db, user_id,
            _NT.SYSTEM,
            {"message": "Your KYC has been approved. Withdrawals are now enabled."},
            title="KYC Approved",
            body="Your identity verification has been approved by our team. You can now make withdrawals.",
            channel=_NC.IN_APP,
        )
        await db.commit()
    except Exception as _e:
        logger.warning(f"KYC approval notification failed for user {user_id}: {_e}")

    logger.info(f"Admin {current_user.id} approved KYC for user {user_id}")
    return {"user_id": user_id, "kyc_status": "approved", "message": "KYC approved and withdrawals enabled."}


@router.post("/admin/kyc/reject/{user_id}")
async def admin_reject_kyc(
    user_id: int,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Admin: reject a pending KYC submission."""
    from app.db.models import User as _User

    if getattr(current_user, "role", "viewer") not in ("admin", "superadmin"):
        raise HTTPException(403, "Admin privileges required.")

    user_res = await db.execute(select(_User).where(_User.id == user_id))
    db_user = user_res.scalar_one_or_none()
    if not db_user:
        raise HTTPException(404, "User not found.")

    kyc_status = getattr(db_user, "kyc_status", "none")
    if kyc_status not in ("pending",):
        raise HTTPException(400, f"Cannot reject KYC with status '{kyc_status}'.")

    if hasattr(db_user, "kyc_status"):
        db_user.kyc_status = "rejected"

    await db.commit()

    try:
        from app.modules.notifications.service import NotificationService as _NS
        from app.modules.notifications.models import NotificationType as _NT, NotificationChannel as _NC
        rejection_body = reason or "Your KYC submission did not meet our verification requirements."
        await _NS.create(
            db, user_id,
            _NT.SYSTEM,
            {"message": rejection_body},
            title="KYC Rejected",
            body=rejection_body,
            channel=_NC.IN_APP,
        )
        await db.commit()
    except Exception as _e:
        logger.warning(f"KYC rejection notification failed for user {user_id}: {_e}")

    logger.info(f"Admin {current_user.id} rejected KYC for user {user_id}")
    return {"user_id": user_id, "kyc_status": "rejected", "message": "KYC rejected. User has been notified."}


@router.get("/admin/kyc/pending")
async def admin_list_pending_kyc(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Admin: list all users with pending KYC submissions."""
    from app.db.models import User as _User

    if getattr(current_user, "role", "viewer") not in ("admin", "superadmin"):
        raise HTTPException(403, "Admin privileges required.")

    result = await db.execute(
        select(_User).where(
            _User.kyc_status == "pending"
        ).order_by(_User.kyc_submitted_at.asc())
    )
    pending_users = result.scalars().all()
    return {
        "total": len(pending_users),
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "kyc_status": getattr(u, "kyc_status", "none"),
                "submitted_at": u.kyc_submitted_at.isoformat() if getattr(u, "kyc_submitted_at", None) else None,
            }
            for u in pending_users
        ],
    }


@router.get("/vitcoin-price")
async def get_vitcoin_price(db: AsyncSession = Depends(get_db)):
    """Get current VITCoin price."""
    pricing = VITCoinPricingEngine(db)
    prices = await pricing.get_current_price()

    result = await db.execute(
        select(VITCoinPriceHistory).order_by(VITCoinPriceHistory.calculated_at.desc()).limit(1)
    )
    last = result.scalar_one_or_none()
    next_update = (last.calculated_at + timedelta(hours=6)).isoformat() if last else None

    return {
        "price_usd": float(prices["usd"]),
        "price_ngn": float(prices["ngn"]),
        "price_usdt": float(prices["usdt"]),
        "price_pi": float(prices["pi"]),
        "circulating_supply": float(await pricing.get_circulating_supply()),
        "rolling_revenue_usd": float(await pricing.get_rolling_revenue()),
        "calculated_at": last.calculated_at.isoformat() if last else None,
        "next_update_at": next_update,
    }
