# app/modules/wallet/routes.py
"""User wallet API endpoints — full production implementation."""

from app.core.cache import cache
from app.core.cache_keys import VITCOIN_PRICE

import csv
import io
import logging
import uuid as _uuid_mod
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.services.telegram_service import create_stars_invoice
from app.modules.wallet.services import WalletService, WithdrawalService, SubscriptionService
from app.modules.wallet.pricing import VITCoinPricingEngine
from app.modules.wallet.models import (
    Currency, WalletSubscriptionPlan, WalletTransaction, WithdrawalRequest,
    VITCoinPriceHistory, PlatformConfig, Wallet, SavingsVault,
    P2POffer, P2POrder,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/wallet", tags=["Wallet"])


# ── Idempotency helper ─────────────────────────────────────────────────

async def _check_idempotency(key: Optional[str], user_id: int, db: AsyncSession) -> Optional[dict]:
    """Return cached result if key was already processed, else None."""
    if not key:
        return None
    cache_key = f"idempotency:{user_id}:{key}"
    cached = await cache.get(cache_key)
    return cached


async def _store_idempotency(key: Optional[str], user_id: int, result: dict) -> None:
    if not key:
        return
    cache_key = f"idempotency:{user_id}:{key}"
    await cache.set(cache_key, result, ttl=86400)


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
    amount: float = Field(..., gt=0)
    currency: str = Field(default="NGN")
    bank_code: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    destination: Optional[str] = None
    destination_type: str = Field(default="bank_account", description="bank_account, usdt_address, pi_wallet, paypal")


class SubscribeRequest(BaseModel):
    plan_id: str
    currency: str


class KYCSubmitRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    date_of_birth: str = Field(..., description="YYYY-MM-DD")
    document_type: str = Field(..., description="passport, national_id, drivers_license, voters_card")
    document_number: str = Field(..., min_length=3, max_length=60)
    nationality: Optional[str] = None


class KYCRejectRequest(BaseModel):
    reason: Optional[str] = None


class StarsInvoiceRequest(BaseModel):
    stars_amount: int = Field(..., gt=0, description="Number of Telegram Stars to invoice")


class WalletResponse(BaseModel):
    ngn_balance: float
    usd_balance: float
    usdt_balance: float
    pi_balance: float
    vitcoin_balance: float
    is_frozen: bool
    kyc_verified: bool


class VITCoinBuyRequest(BaseModel):
    amount_ngn: Optional[float] = Field(None, gt=0)
    amount_usd: Optional[float] = Field(None, gt=0)


class VITCoinSellRequest(BaseModel):
    vitcoin_amount: float = Field(..., gt=0)


class StakeRequest(BaseModel):
    amount: float = Field(..., gt=0)


class UnstakeRequest(BaseModel):
    amount: float = Field(..., gt=0)


class VaultCreateRequest(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field(default="VITCoin")
    lock_period_days: int = Field(..., description="30, 90, 180, or 365")


class P2POfferCreateRequest(BaseModel):
    offer_type: str = Field(..., description="buy or sell")
    amount: float = Field(..., gt=0)
    currency: str = Field(default="VITCoin")
    rate_ngn: float = Field(..., gt=0)
    min_order: float = Field(..., gt=0)
    max_order: float = Field(..., gt=0)
    payment_method: str = Field(default="bank_transfer")
    payment_details: Optional[dict] = None


class P2POrderCreateRequest(BaseModel):
    offer_id: str
    amount: float = Field(..., gt=0)


class P2PDisputeRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500)


# ── APY table by lock period ───────────────────────────────────────────
_VAULT_APY: dict[int, Decimal] = {
    30: Decimal("5.00"),
    90: Decimal("8.00"),
    180: Decimal("12.00"),
    365: Decimal("18.00"),
}


# ── Helper: get or fail wallet ─────────────────────────────────────────
async def _require_wallet(user_id: int, db: AsyncSession) -> Wallet:
    service = WalletService(db)
    return await service.get_or_create_wallet(user_id)


# ══════════════════════════════════════════════════════════════════════
# WALLET OVERVIEW
# ══════════════════════════════════════════════════════════════════════

@router.get("")
async def get_wallet_overview(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Wallet overview: balances + staked + pending withdrawals + 30d earnings."""
    wallet = await _require_wallet(current_user.id, db)

    pending_total_result = await db.execute(
        select(func.coalesce(func.sum(WithdrawalRequest.amount), 0))
        .where(
            WithdrawalRequest.wallet_id == wallet.id,
            WithdrawalRequest.status.in_(["pending", "manual_review"]),
        )
    )
    pending_withdrawals = float(pending_total_result.scalar() or 0)

    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
    earnings_result = await db.execute(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0))
        .where(
            WalletTransaction.wallet_id == wallet.id,
            WalletTransaction.direction == "credit",
            WalletTransaction.type.in_(["earn", "reward", "referral_claim", "stake"]),
            WalletTransaction.status == "confirmed",
            WalletTransaction.created_at >= cutoff_30d,
        )
    )
    earnings_30d = float(earnings_result.scalar() or 0)

    pricing = VITCoinPricingEngine(db)
    prices = await pricing.get_current_price()

    total_usd = (
        float(wallet.ngn_balance) * float(prices.get("usd", Decimal("0.10"))) / 1580.0
        + float(wallet.usd_balance)
        + float(wallet.usdt_balance)
        + float(wallet.vitcoin_balance) * float(prices.get("usd", Decimal("0.10")))
        + float(wallet.staked_vitcoin_balance) * float(prices.get("usd", Decimal("0.10")))
    )

    return {
        "vitcoin_balance": float(wallet.vitcoin_balance),
        "ngn_balance": float(wallet.ngn_balance),
        "usd_balance": float(wallet.usd_balance),
        "usdt_balance": float(wallet.usdt_balance),
        "pi_balance": float(wallet.pi_balance),
        "staked_vitcoin": float(wallet.staked_vitcoin_balance),
        "pending_withdrawals_total": pending_withdrawals,
        "earnings_30d": earnings_30d,
        "total_balance_usd": round(total_usd, 4),
        "is_frozen": wallet.is_frozen,
        "kyc_verified": wallet.kyc_verified,
        "vitcoin_price_usd": float(prices.get("usd", Decimal("0.10"))),
    }


@router.get("/vitcoin-balance")
async def get_vitcoin_balance(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias: return VITCoin balance for the current user."""
    service = WalletService(db)
    wallet = await service.get_or_create_wallet(current_user.id)
    return {"vitcoin_balance": float(wallet.vitcoin_balance), "user_id": current_user.id}


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


# ══════════════════════════════════════════════════════════════════════
# TRANSACTIONS
# ══════════════════════════════════════════════════════════════════════

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
                "description": t.description,
                "fee_amount": float(t.fee_amount),
                "created_at": t.created_at.isoformat(),
                "processed_at": t.processed_at.isoformat() if t.processed_at else None,
            }
            for t in transactions
        ],
    }


@router.get("/transactions/{tx_id}")
async def get_transaction_detail(
    tx_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single transaction detail."""
    result = await db.execute(
        select(WalletTransaction).where(
            WalletTransaction.id == tx_id,
            WalletTransaction.user_id == current_user.id,
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "Transaction not found")
    return {
        "id": tx.id,
        "type": tx.type,
        "currency": tx.currency,
        "amount": float(tx.amount),
        "direction": tx.direction,
        "status": tx.status,
        "reference": tx.reference,
        "description": tx.description,
        "fee_amount": float(tx.fee_amount),
        "fee_currency": tx.fee_currency,
        "rate_snapshot": tx.rate_snapshot,
        "tx_metadata": tx.tx_metadata,
        "created_at": tx.created_at.isoformat(),
        "processed_at": tx.processed_at.isoformat() if tx.processed_at else None,
    }


# ══════════════════════════════════════════════════════════════════════
# DEPOSITS
# ══════════════════════════════════════════════════════════════════════

@router.post("/deposit/initiate")
async def initiate_deposit(
    request: DepositInitiateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a deposit — calls Paystack when keys are configured."""
    from app.config import PAYSTACK_SECRET_KEY, REPLIT_DEV_DOMAIN, PUBLIC_APP_URL

    service = WalletService(db)
    wallet = await service.get_or_create_wallet(current_user.id)
    ref = f"DEP-{current_user.id}-{_uuid_mod.uuid4().hex[:8].upper()}"

    payment_link = None
    client_secret = None
    gateway_error = None

    if request.method == "paystack":
        paystack_key = PAYSTACK_SECRET_KEY
        if paystack_key:
            try:
                import httpx as _httpx
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
                            "metadata": {"user_id": current_user.id, "vit_ref": ref},
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

    try:
        pending_tx = WalletTransaction(
            id=str(_uuid_mod.uuid4()),
            user_id=current_user.id,
            wallet_id=wallet.id,
            type="deposit",
            currency=request.currency.upper(),
            amount=Decimal(str(request.amount)),
            direction="credit",
            status="pending",
            reference=ref,
            description=f"Deposit via {request.method}",
            tx_metadata={
                "method": request.method,
                "gateway_error": gateway_error,
                "payment_link": payment_link,
            },
        )
        db.add(pending_tx)
        await db.commit()
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
        except Exception as _ne:
            logger.warning(f"Deposit notification failed: {_ne}")
    except Exception as _tx_err:
        logger.error(f"Failed to record pending deposit: {_tx_err}")
        await db.rollback()

    fallback_link = payment_link or f"https://paystack.com/pay/vit-sports?ref={ref}"

    return {
        "status": "pending",
        "reference": ref,
        "payment_link": fallback_link,
        "client_secret": client_secret,
        "gateway_error": gateway_error,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "currency": request.currency,
        "amount": request.amount,
        "method": request.method,
    }


@router.get("/deposit/verify/{reference}")
async def verify_deposit_get(
    reference: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually verify a Paystack payment by reference (GET polling variant)."""
    return await _do_verify_deposit(reference, "NGN", current_user, db)


@router.post("/deposit/verify")
async def verify_deposit(
    request: DepositVerifyRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a completed deposit and credit the wallet if confirmed."""
    return await _do_verify_deposit(request.reference, request.currency, current_user, db)


async def _do_verify_deposit(reference: str, currency: str, current_user, db: AsyncSession) -> dict:
    from app.config import PAYSTACK_SECRET_KEY

    verified_amount = None
    verified_status = "failed"
    verified_currency = currency

    paystack_key = PAYSTACK_SECRET_KEY
    if paystack_key:
        try:
            import httpx as _httpx
            async with _httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://api.paystack.co/transaction/verify/{reference}",
                    headers={"Authorization": f"Bearer {paystack_key}"},
                )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") and data["data"]["status"] == "success":
                    verified_amount = Decimal(str(data["data"]["amount"])) / 100
                    verified_status = "confirmed"
                    verified_currency = data["data"].get("currency", currency)
        except Exception as _e:
            logger.warning(f"Paystack verification failed for ref {reference}: {_e}")

    if verified_status == "confirmed" and verified_amount is not None:
        try:
            service = WalletService(db)
            wallet = await service.get_or_create_wallet(current_user.id)
            tx_result = await db.execute(
                select(WalletTransaction).where(
                    WalletTransaction.reference == reference,
                    WalletTransaction.user_id == current_user.id,
                )
            )
            tx = tx_result.scalar_one_or_none()
            if tx:
                if tx.status == "confirmed":
                    return {"status": "confirmed", "amount": float(tx.amount), "currency": tx.currency, "reference": reference}
                tx.status = "confirmed"
                tx.amount = verified_amount
                tx.processed_at = datetime.now(timezone.utc)
            else:
                db.add(WalletTransaction(
                    id=str(_uuid_mod.uuid4()),
                    user_id=current_user.id,
                    wallet_id=wallet.id,
                    type="deposit",
                    currency=verified_currency.upper(),
                    amount=verified_amount,
                    direction="credit",
                    status="confirmed",
                    reference=reference,
                    description="Deposit confirmed via Paystack",
                    processed_at=datetime.now(timezone.utc),
                ))
            try:
                cur_enum = Currency(verified_currency.upper())
            except ValueError:
                cur_enum = Currency.NGN
            await service.credit(
                wallet_id=wallet.id,
                user_id=current_user.id,
                currency=cur_enum,
                amount=verified_amount,
                tx_type="deposit",
                reference=f"{reference}-CREDIT",
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            if isinstance(e, HTTPException): raise e
            logger.error(f"Transaction error: {e}")
            raise HTTPException(500, "Internal Server Error")
        try:
            from app.modules.tasks.service import TaskService
            try:
                await TaskService.update_task_progress(db, current_user.id, 6, 1)
                await db.commit()
            except Exception as e:
                await db.rollback()
                if isinstance(e, HTTPException): raise e
                logger.error(f"Transaction error: {e}")
                raise HTTPException(500, "Internal Server Error")
        except Exception as _e:
            logger.warning(f"Task progress update failed: {_e}")
        try:
            from app.modules.referral.routes import process_deposit_commission
            await process_deposit_commission(db, current_user.id, verified_amount)
        except Exception as _re:
            logger.warning(f"Referral commission failed: {_re}")
        return {"status": "confirmed", "amount": float(verified_amount), "currency": verified_currency, "reference": reference}

    return {"status": verified_status, "reference": reference, "currency": currency}


# ══════════════════════════════════════════════════════════════════════
# KYC
# ══════════════════════════════════════════════════════════════════════

@router.post("/kyc/submit")
async def submit_kyc(
    body: KYCSubmitRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit KYC identity information for verification."""
    from app.db.models import User as _User

    result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(404, "Wallet not found")

    if wallet.kyc_verified:
        return {"kyc_verified": True, "kyc_status": "approved", "message": "KYC already verified."}

    user_res = await db.execute(select(_User).where(_User.id == current_user.id))
    db_user = user_res.scalar_one_or_none()
    if db_user:
        current_status = getattr(db_user, "kyc_status", "none")
        if current_status == "pending":
            return {"kyc_verified": False, "kyc_status": "pending", "message": "Your KYC submission is already under review."}
        if hasattr(db_user, "kyc_data"):
            db_user.kyc_data = {
                "full_name": body.full_name,
                "date_of_birth": body.date_of_birth,
                "document_type": body.document_type,
                "document_number": body.document_number,
                "nationality": body.nationality,
            }
        if hasattr(db_user, "kyc_status"):
            db_user.kyc_status = "pending"
        if hasattr(db_user, "kyc_submitted_at"):
            db_user.kyc_submitted_at = datetime.now(timezone.utc)

    await db.commit()
    try:
        from app.modules.notifications.service import NotificationService as _NS
        from app.modules.notifications.models import NotificationType as _NT, NotificationChannel as _NC
        await _NS.create(db, current_user.id, _NT.SYSTEM,
            {"message": "KYC received and under review."},
            title="KYC Submitted — Under Review",
            body="Your identity submission is under review. You will be notified once approved.",
            channel=_NC.IN_APP)
        await db.commit()
    except Exception as _e:
        logger.warning(f"KYC notification failed: {_e}")

    return {"kyc_verified": False, "kyc_status": "pending", "message": "KYC submitted successfully. Under review."}


# ══════════════════════════════════════════════════════════════════════
# WITHDRAWALS
# ══════════════════════════════════════════════════════════════════════

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

    destination = request.destination or request.account_number or ""
    if not destination:
        raise HTTPException(400, "account_number or destination is required")

    kyc_status = getattr(current_user, "kyc_status", "none") or "none"

    limits_result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == "withdrawal_limits"))
    limits_config = limits_result.scalar_one_or_none()
    kyc_threshold = Decimal("50000")
    if limits_config:
        kyc_threshold = Decimal(str(limits_config.value.get("kyc_threshold", 50000)))

    if Decimal(str(request.amount)) > kyc_threshold and not kyc_status == "approved":
        raise HTTPException(403, f"KYC verification required for withdrawals above {kyc_threshold}.")

    auto_limits_result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == "auto_withdrawal_limits"))
    auto_limits_config = auto_limits_result.scalar_one_or_none()
    role = getattr(current_user, "role", "viewer")
    auto_approve_limit = Decimal("0")
    if auto_limits_config:
        auto_approve_limit = Decimal(str(auto_limits_config.value.get(role, 0)))

    try:
        wallet_service = WalletService(db)
        withdrawal_service = WithdrawalService(db, wallet_service)
        wallet = await wallet_service.get_or_create_wallet(current_user.id)

        try:
            wr = await withdrawal_service.create_withdrawal_request(
                user_id=current_user.id,
                wallet_id=wallet.id,
                currency=currency,
                amount=Decimal(str(request.amount)),
                destination=destination,
                destination_type=request.destination_type,
                auto_approve_limit=auto_approve_limit,
                kyc_status=kyc_status,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))

        if request.bank_code or request.account_name:
            wr.bank_code = request.bank_code
            wr.account_number = request.account_number
            wr.account_name = request.account_name

        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
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
        "currency": withdrawal.currency,
        "destination": withdrawal.destination,
        "bank_code": withdrawal.bank_code,
        "account_number": withdrawal.account_number,
        "account_name": withdrawal.account_name,
        "review_note": withdrawal.review_note,
        "requested_at": withdrawal.requested_at.isoformat(),
        "processed_at": withdrawal.processed_at.isoformat() if withdrawal.processed_at else None,
    }


@router.get("/withdrawals")
async def list_withdrawals(
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's withdrawal requests, newest first."""
    result = await db.execute(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.user_id == current_user.id)
        .order_by(WithdrawalRequest.requested_at.desc())
        .limit(limit)
    )
    withdrawals = result.scalars().all()
    return {
        "withdrawals": [
            {
                "id": str(w.id),
                "currency": w.currency,
                "amount": float(w.amount),
                "fee": float(w.fee_amount),
                "net_amount": float(w.net_amount),
                "destination": w.destination,
                "bank_code": w.bank_code,
                "account_number": w.account_number,
                "account_name": w.account_name,
                "destination_type": w.destination_type,
                "status": w.status,
                "auto_approved": w.auto_approved,
                "review_note": w.review_note,
                "requested_at": w.requested_at.isoformat(),
                "processed_at": w.processed_at.isoformat() if w.processed_at else None,
            }
            for w in withdrawals
        ],
        "total": len(withdrawals),
    }


# ══════════════════════════════════════════════════════════════════════
# VITCOIN PRICE
# ══════════════════════════════════════════════════════════════════════

@router.get("/vitcoin/price")
async def get_vitcoin_price_v2(db: AsyncSession = Depends(get_db)):
    """Current VITCoin price with 24h change, 7d array, supply, market cap."""
    _cached = await cache.get(VITCOIN_PRICE)
    if _cached:
        return _cached

    pricing = VITCoinPricingEngine(db)
    prices = await pricing.get_current_price()
    supply = await pricing.get_circulating_supply()

    last_result = await db.execute(
        select(VITCoinPriceHistory)
        .order_by(VITCoinPriceHistory.calculated_at.desc())
        .limit(1)
    )
    last = last_result.scalar_one_or_none()

    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    prev_result = await db.execute(
        select(VITCoinPriceHistory)
        .where(VITCoinPriceHistory.calculated_at <= cutoff_24h)
        .order_by(VITCoinPriceHistory.calculated_at.desc())
        .limit(1)
    )
    prev = prev_result.scalar_one_or_none()
    change_24h = 0.0
    if prev and float(prev.price_usd) > 0:
        change_24h = round((float(prices["usd"]) - float(prev.price_usd)) / float(prev.price_usd) * 100, 4)

    cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)
    week_result = await db.execute(
        select(VITCoinPriceHistory)
        .where(VITCoinPriceHistory.calculated_at >= cutoff_7d)
        .order_by(VITCoinPriceHistory.calculated_at.asc())
    )
    week_rows = week_result.scalars().all()
    price_7d = [float(r.price_usd) for r in week_rows]

    res = {
        "price_usd": float(prices["usd"]),
        "price_ngn": float(prices["ngn"]),
        "price_usdt": float(prices["usdt"]),
        "price_pi": float(prices["pi"]),
        "change_24h_pct": change_24h,
        "price_7d": price_7d,
        "circulating_supply": float(supply),
        "market_cap_usd": float(prices["usd"] * supply),
        "calculated_at": last.calculated_at.isoformat() if last else None,
        "next_update_at": (last.calculated_at + timedelta(hours=6)).isoformat() if last else None,
    }
    await cache.set(VITCOIN_PRICE, res, ttl=30)
    return res


@router.get("/vitcoin-price")
async def get_vitcoin_price(db: AsyncSession = Depends(get_db)):
    """Get current VITCoin price (legacy path)."""
    return await get_vitcoin_price_v2(db)


@router.get("/vitcoin/price/history")
async def get_vitcoin_price_history_v2(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Return VITCoin OHLCV price history for up to 365 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(VITCoinPriceHistory)
        .where(VITCoinPriceHistory.calculated_at >= cutoff)
        .order_by(VITCoinPriceHistory.calculated_at.asc())
    )
    rows = result.scalars().all()
    history = []
    for r in rows:
        p = float(r.price_usd)
        history.append({
            "date": r.calculated_at.isoformat(),
            "open": p,
            "high": round(p * 1.005, 8),
            "low": round(p * 0.995, 8),
            "close": p,
            "volume": float(r.circulating_supply),
            "price_usd": p,
        })
    return {"history": history, "days": days, "count": len(history)}


@router.get("/vitcoin-price/history")
async def get_vitcoin_price_history(
    days: int = Query(7, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Return VITCoin price history (legacy path)."""
    return await get_vitcoin_price_history_v2(days, db)


# ══════════════════════════════════════════════════════════════════════
# VITCOIN BUY / SELL
# ══════════════════════════════════════════════════════════════════════

@router.post("/vitcoin/buy")
async def buy_vitcoin(
    request: VITCoinBuyRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Buy VITCoin with NGN or USD. Idempotency key required."""
    cached = await _check_idempotency(x_idempotency_key, current_user.id, db)
    if cached:
        return cached

    if not request.amount_ngn and not request.amount_usd:
        raise HTTPException(400, "Provide amount_ngn or amount_usd")

    pricing = VITCoinPricingEngine(db)
    prices = await pricing.get_current_price()
    price_usd = prices["usd"]

    fee_result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == "conversion_fee_pct"))
    fee_config = fee_result.scalar_one_or_none()
    fee_pct = Decimal(str(fee_config.value.get("value", 1.5))) if fee_config else Decimal("1.5")

    if request.amount_ngn:
        fiat_currency = Currency.NGN
        fiat_amount = Decimal(str(request.amount_ngn))
        ngn_per_usd = prices["ngn"] / price_usd if price_usd > 0 else Decimal("1580")
        fiat_in_usd = fiat_amount / ngn_per_usd
    else:
        fiat_currency = Currency.USD
        fiat_amount = Decimal(str(request.amount_usd))
        fiat_in_usd = fiat_amount

    fee_usd = fiat_in_usd * (fee_pct / Decimal("100"))
    net_usd = fiat_in_usd - fee_usd
    vitcoin_received = net_usd / price_usd if price_usd > 0 else Decimal("0")

    try:
        service = WalletService(db)
        wallet = await service.get_or_create_wallet(current_user.id)

        fiat_attr = f"{fiat_currency.value.lower()}_balance"
        current_fiat = getattr(wallet, fiat_attr, Decimal("0")) or Decimal("0")
        if current_fiat < fiat_amount:
            raise HTTPException(402, f"Insufficient {fiat_currency.value} balance")

        ref_base = f"BUY-{current_user.id}-{_uuid_mod.uuid4().hex[:8].upper()}"

        await service.debit(
            wallet_id=wallet.id, user_id=current_user.id,
            currency=fiat_currency, amount=fiat_amount,
            tx_type="buy", reference=f"{ref_base}-DEBIT",
            metadata={"vitcoin_received": str(vitcoin_received), "rate": str(price_usd)},
        )
        await service.credit(
            wallet_id=wallet.id, user_id=current_user.id,
            currency=Currency.VITCOIN, amount=vitcoin_received,
            tx_type="buy", reference=f"{ref_base}-CREDIT",
        )

        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
    result = {
        "status": "success",
        "fiat_spent": float(fiat_amount),
        "fiat_currency": fiat_currency.value,
        "vitcoin_received": float(vitcoin_received),
        "price_usd": float(price_usd),
        "fee_pct": float(fee_pct),
        "reference": ref_base,
    }
    await _store_idempotency(x_idempotency_key, current_user.id, result)
    return result


@router.post("/vitcoin/sell")
async def sell_vitcoin(
    request: VITCoinSellRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sell VITCoin for NGN. Idempotency key required."""
    cached = await _check_idempotency(x_idempotency_key, current_user.id, db)
    if cached:
        return cached

    pricing = VITCoinPricingEngine(db)
    prices = await pricing.get_current_price()
    price_usd = prices["usd"]

    fee_result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == "conversion_fee_pct"))
    fee_config = fee_result.scalar_one_or_none()
    fee_pct = Decimal(str(fee_config.value.get("value", 1.5))) if fee_config else Decimal("1.5")

    vitcoin_amount = Decimal(str(request.vitcoin_amount))
    usd_gross = vitcoin_amount * price_usd
    fee_usd = usd_gross * (fee_pct / Decimal("100"))
    net_usd = usd_gross - fee_usd
    ngn_per_usd = prices["ngn"] / price_usd if price_usd > 0 else Decimal("1580")
    ngn_received = net_usd * ngn_per_usd

    try:
        service = WalletService(db)
        wallet = await service.get_or_create_wallet(current_user.id)

        if (wallet.vitcoin_balance or Decimal("0")) < vitcoin_amount:
            raise HTTPException(402, "Insufficient VITCoin balance")

        ref_base = f"SELL-{current_user.id}-{_uuid_mod.uuid4().hex[:8].upper()}"

        await service.debit(
            wallet_id=wallet.id, user_id=current_user.id,
            currency=Currency.VITCOIN, amount=vitcoin_amount,
            tx_type="sell", reference=f"{ref_base}-DEBIT",
            metadata={"ngn_received": str(ngn_received), "rate": str(price_usd)},
        )
        await service.credit(
            wallet_id=wallet.id, user_id=current_user.id,
            currency=Currency.NGN, amount=ngn_received,
            tx_type="sell", reference=f"{ref_base}-CREDIT",
        )

        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
    result = {
        "status": "success",
        "vitcoin_sold": float(vitcoin_amount),
        "ngn_received": float(ngn_received),
        "price_usd": float(price_usd),
        "fee_pct": float(fee_pct),
        "reference": ref_base,
    }
    await _store_idempotency(x_idempotency_key, current_user.id, result)
    return result


# ══════════════════════════════════════════════════════════════════════
# STAKING
# ══════════════════════════════════════════════════════════════════════

@router.post("/stake")
async def stake_vitcoin(
    request: StakeRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stake VITCoin. Debit vitcoin_balance, credit staked_vitcoin_balance."""
    min_stake_result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == "vitcoin_min_stake"))
    min_stake_config = min_stake_result.scalar_one_or_none()
    min_stake = Decimal(str(min_stake_config.value.get("value", 10))) if min_stake_config else Decimal("10")

    amount = Decimal(str(request.amount))
    if amount < min_stake:
        raise HTTPException(400, f"Minimum stake is {min_stake} VITCoin")

    try:
        service = WalletService(db)
        wallet = await service.get_or_create_wallet(current_user.id)

        if (wallet.vitcoin_balance or Decimal("0")) < amount:
            raise HTTPException(402, "Insufficient VITCoin balance")

        ref = f"STAKE-{current_user.id}-{_uuid_mod.uuid4().hex[:8].upper()}"

        wallet.vitcoin_balance = (wallet.vitcoin_balance or Decimal("0")) - amount
        wallet.staked_vitcoin_balance = (wallet.staked_vitcoin_balance or Decimal("0")) + amount

        db.add(WalletTransaction(
            id=str(_uuid_mod.uuid4()),
            user_id=current_user.id,
            wallet_id=wallet.id,
            type="stake",
            currency="VITCoin",
            amount=amount,
            direction="debit",
            status="confirmed",
            reference=ref,
            description=f"Staked {float(amount):.4f} VITCoin",
            processed_at=datetime.now(timezone.utc),
        ))

        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
    return {
        "status": "staked",
        "amount": float(amount),
        "vitcoin_balance": float(wallet.vitcoin_balance),
        "staked_balance": float(wallet.staked_vitcoin_balance),
        "validator_eligible": float(wallet.staked_vitcoin_balance) >= 100,
        "reference": ref,
    }


@router.post("/unstake")
async def unstake_vitcoin(
    request: UnstakeRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unstake VITCoin and return to available balance."""
    amount = Decimal(str(request.amount))

    try:
        service = WalletService(db)
        wallet = await service.get_or_create_wallet(current_user.id)

        if (wallet.staked_vitcoin_balance or Decimal("0")) < amount:
            raise HTTPException(402, "Insufficient staked VITCoin balance")

        ref = f"UNSTAKE-{current_user.id}-{_uuid_mod.uuid4().hex[:8].upper()}"

        wallet.staked_vitcoin_balance = (wallet.staked_vitcoin_balance or Decimal("0")) - amount
        wallet.vitcoin_balance = (wallet.vitcoin_balance or Decimal("0")) + amount

        db.add(WalletTransaction(
            id=str(_uuid_mod.uuid4()),
            user_id=current_user.id,
            wallet_id=wallet.id,
            type="unstake",
            currency="VITCoin",
            amount=amount,
            direction="credit",
            status="confirmed",
            reference=ref,
            description=f"Unstaked {float(amount):.4f} VITCoin",
            processed_at=datetime.now(timezone.utc),
        ))

        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
    return {
        "status": "unstaked",
        "amount": float(amount),
        "vitcoin_balance": float(wallet.vitcoin_balance),
        "staked_balance": float(wallet.staked_vitcoin_balance),
        "reference": ref,
    }


@router.get("/stake/status")
async def get_stake_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return staked amount, validator eligibility, and estimated accrued rewards."""
    wallet = await _require_wallet(current_user.id, db)

    apy_result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == "staking_apy_pct"))
    apy_config = apy_result.scalar_one_or_none()
    apy_pct = float(apy_config.value.get("value", 8.0)) if apy_config else 8.0

    staked = float(wallet.staked_vitcoin_balance or 0)
    daily_reward = staked * apy_pct / 365 / 100

    return {
        "staked_amount": staked,
        "vitcoin_balance": float(wallet.vitcoin_balance or 0),
        "validator_eligible": staked >= 100,
        "apy_pct": apy_pct,
        "estimated_daily_reward": round(daily_reward, 8),
        "unlock_date": None,
    }


# ══════════════════════════════════════════════════════════════════════
# CURRENCY CONVERSION
# ══════════════════════════════════════════════════════════════════════

@router.get("/convert/quote")
async def get_conversion_quote(
    from_currency: str = Query(...),
    to_currency: str = Query(...),
    amount: float = Query(..., gt=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Dry-run conversion quote. No state change."""
    try:
        from_cur = Currency(from_currency)
        to_cur = Currency(to_currency)
    except ValueError:
        raise HTTPException(400, "Invalid currency")

    pricing = VITCoinPricingEngine(db)
    result = await pricing.calculate_conversion_amount(from_cur, to_cur, Decimal(str(amount)))

    rate_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
    return {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "from_amount": float(amount),
        "received_amount": float(result["to_amount"]),
        "fee": float(result["fee"]),
        "fee_pct": float(result["fee_pct"]),
        "rate": float(result["rate"]),
        "rate_expires_at": rate_expires_at,
    }


@router.post("/convert")
async def convert_currency(
    request: ConvertRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert between currencies. Idempotency key required."""
    cached = await _check_idempotency(x_idempotency_key, current_user.id, db)
    if cached:
        return cached

    try:
        from_cur = Currency(request.from_currency)
        to_cur = Currency(request.to_currency)
    except ValueError:
        raise HTTPException(400, "Invalid currency")

    try:
        service = WalletService(db)
        wallet = await service.get_or_create_wallet(current_user.id)

        fee_result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == "conversion_fee_pct"))
        fee_config = fee_result.scalar_one_or_none()
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
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
    updated = await _require_wallet(current_user.id, db)
    result = {
        "from_currency": request.from_currency,
        "to_currency": request.to_currency,
        "from_amount": request.amount,
        "to_amount": float(converted_amount),
        "fee": float(debit_tx.fee_amount),
        "fee_pct": float(fee_pct),
        "new_balances": {
            "ngn": float(updated.ngn_balance),
            "usd": float(updated.usd_balance),
            "usdt": float(updated.usdt_balance),
            "pi": float(updated.pi_balance),
            "vitcoin": float(updated.vitcoin_balance),
        },
    }
    await _store_idempotency(x_idempotency_key, current_user.id, result)
    return result


# ══════════════════════════════════════════════════════════════════════
# P2P EXCHANGE
# ══════════════════════════════════════════════════════════════════════

@router.get("/p2p/offers")
async def list_p2p_offers(
    currency: Optional[str] = Query(None),
    offer_type: Optional[str] = Query(None, description="buy or sell"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List active P2P offers."""
    q = select(P2POffer).where(P2POffer.status == "active")
    if currency:
        q = q.where(P2POffer.currency == currency.upper())
    if offer_type:
        q = q.where(P2POffer.offer_type == offer_type.lower())
    q = q.order_by(P2POffer.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    offers = result.scalars().all()
    return {
        "offers": [
            {
                "id": o.id,
                "offer_type": o.offer_type,
                "currency": o.currency,
                "available_amount": float(o.available_amount),
                "rate_ngn": float(o.rate_ngn),
                "min_order": float(o.min_order),
                "max_order": float(o.max_order),
                "payment_method": o.payment_method,
                "user_id": o.user_id,
                "created_at": o.created_at.isoformat(),
            }
            for o in offers
        ],
        "page": page,
        "limit": limit,
    }


@router.post("/p2p/offers", status_code=201)
async def create_p2p_offer(
    request: P2POfferCreateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a P2P offer. Escrows VITCoin immediately for sell offers."""
    if request.offer_type not in ("buy", "sell"):
        raise HTTPException(400, "offer_type must be buy or sell")
    if request.min_order > request.max_order:
        raise HTTPException(400, "min_order must be ≤ max_order")
    if request.max_order > request.amount:
        raise HTTPException(400, "max_order must be ≤ offer amount")

    try:
        service = WalletService(db)
        wallet = await service.get_or_create_wallet(current_user.id)

        escrowed = Decimal("0")
        if request.offer_type == "sell":
            amount = Decimal(str(request.amount))
            if (wallet.vitcoin_balance or Decimal("0")) < amount:
                raise HTTPException(402, "Insufficient VITCoin balance for escrow")
            wallet.vitcoin_balance = (wallet.vitcoin_balance or Decimal("0")) - amount
            escrowed = amount
            db.add(WalletTransaction(
                id=str(_uuid_mod.uuid4()),
                user_id=current_user.id,
                wallet_id=wallet.id,
                type="p2p_escrow",
                currency="VITCoin",
                amount=amount,
                direction="debit",
                status="confirmed",
                reference=f"P2P-ESC-{_uuid_mod.uuid4().hex[:8].upper()}",
                description="P2P sell offer escrow",
                processed_at=datetime.now(timezone.utc),
            ))

        offer = P2POffer(
            user_id=current_user.id,
            wallet_id=wallet.id,
            offer_type=request.offer_type,
            currency=request.currency.upper(),
            total_amount=Decimal(str(request.amount)),
            available_amount=Decimal(str(request.amount)),
            escrowed_amount=escrowed,
            rate_ngn=Decimal(str(request.rate_ngn)),
            min_order=Decimal(str(request.min_order)),
            max_order=Decimal(str(request.max_order)),
            payment_method=request.payment_method,
            payment_details=request.payment_details,
            status="active",
        )
        db.add(offer)
        await db.flush()

        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
    return {
        "id": offer.id,
        "offer_type": offer.offer_type,
        "currency": offer.currency,
        "amount": float(offer.total_amount),
        "rate_ngn": float(offer.rate_ngn),
        "status": offer.status,
    }


@router.delete("/p2p/offers/{offer_id}", status_code=200)
async def cancel_p2p_offer(
    offer_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel own P2P offer and release escrow if sell offer."""
    result = await db.execute(select(P2POffer).where(P2POffer.id == offer_id))
    offer = result.scalar_one_or_none()
    if not offer:
        raise HTTPException(404, "Offer not found")
    if offer.user_id != current_user.id:
        raise HTTPException(403, "Not your offer")
    if offer.status not in ("active", "paused"):
        raise HTTPException(400, "Offer cannot be cancelled in its current state")

    try:
        db.add(offer)
        offer.status = "cancelled"
        if offer.offer_type == "sell" and offer.escrowed_amount > 0:
            service = WalletService(db)
            wallet = await service.get_or_create_wallet(current_user.id)
            wallet.vitcoin_balance = (wallet.vitcoin_balance or Decimal("0")) + offer.escrowed_amount
            db.add(WalletTransaction(
                id=str(_uuid_mod.uuid4()),
                user_id=current_user.id,
                wallet_id=wallet.id,
                type="p2p_refund",
                currency="VITCoin",
                amount=offer.escrowed_amount,
                direction="credit",
                status="confirmed",
                reference=f"P2P-REF-{_uuid_mod.uuid4().hex[:8].upper()}",
                description="P2P offer cancelled — escrow released",
                processed_at=datetime.now(timezone.utc),
            ))
            offer.escrowed_amount = Decimal("0")

        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
    return {"status": "cancelled", "offer_id": offer_id}


@router.post("/p2p/orders", status_code=201)
async def create_p2p_order(
    request: P2POrderCreateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a trade against a P2P offer."""
    result = await db.execute(select(P2POffer).where(P2POffer.id == request.offer_id))
    offer = result.scalar_one_or_none()
    if not offer or offer.status != "active":
        raise HTTPException(404, "Offer not found or inactive")
    if offer.user_id == current_user.id:
        raise HTTPException(400, "Cannot trade against your own offer")

    amount = Decimal(str(request.amount))
    if amount < offer.min_order or amount > offer.max_order:
        raise HTTPException(400, f"Amount must be between {offer.min_order} and {offer.max_order}")
    if amount > offer.available_amount:
        raise HTTPException(400, "Requested amount exceeds offer availability")

    fiat_total = amount * offer.rate_ngn
    buyer_id = current_user.id if offer.offer_type == "sell" else offer.user_id
    seller_id = offer.user_id if offer.offer_type == "sell" else current_user.id

    try:
        db.add(offer)
        offer.available_amount = offer.available_amount - amount

        order = P2POrder(
            offer_id=offer.id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            amount=amount,
            rate_ngn=offer.rate_ngn,
            fiat_total_ngn=fiat_total,
            status="pending",
        )
        db.add(order)
        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"P2P create order error: {e}")
        raise HTTPException(500, "Failed to place order")

    return {
        "id": order.id,
        "offer_id": offer.id,
        "amount": float(amount),
        "rate_ngn": float(offer.rate_ngn),
        "fiat_total_ngn": float(fiat_total),
        "status": "pending",
        "buyer_id": buyer_id,
        "seller_id": seller_id,
    }


@router.post("/p2p/orders/{order_id}/confirm-payment")
async def p2p_confirm_payment(
    order_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Buyer confirms fiat has been sent."""
    result = await db.execute(select(P2POrder).where(P2POrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.buyer_id != current_user.id:
        raise HTTPException(403, "Only the buyer can confirm payment")
    if order.status != "pending":
        raise HTTPException(400, f"Order is already {order.status}")

    try:
        db.add(order)
        order.status = "payment_sent"
        order.payment_confirmed_at = datetime.now(timezone.utc)

        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
    return {"order_id": order_id, "status": "payment_sent"}


@router.post("/p2p/orders/{order_id}/release")
async def p2p_release_escrow(
    order_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Seller releases escrowed VITCoin to buyer."""
    result = await db.execute(select(P2POrder).where(P2POrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.seller_id != current_user.id:
        raise HTTPException(403, "Only the seller can release escrow")
    if order.status != "payment_sent":
        raise HTTPException(400, "Order must be in payment_sent state")

    try:
        service = WalletService(db)
        buyer_wallet = await service.get_or_create_wallet(order.buyer_id)

        ref = f"P2P-REL-{_uuid_mod.uuid4().hex[:8].upper()}"
        buyer_wallet.vitcoin_balance = (buyer_wallet.vitcoin_balance or Decimal("0")) + order.amount
        release_tx = WalletTransaction(
            id=str(_uuid_mod.uuid4()),
            user_id=order.buyer_id,
            wallet_id=buyer_wallet.id,
            type="p2p_release",
            currency="VITCoin",
            amount=order.amount,
            direction="credit",
            status="confirmed",
            reference=ref,
            description=f"P2P trade completed — {float(order.amount):.4f} VITCoin received",
            processed_at=datetime.now(timezone.utc),
        )
        db.add(release_tx)
        order.release_tx_id = release_tx.id
        order.status = "completed"
        order.completed_at = datetime.now(timezone.utc)

        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
    return {"order_id": order_id, "status": "completed", "amount_released": float(order.amount)}


@router.post("/p2p/orders/{order_id}/dispute")
async def p2p_raise_dispute(
    order_id: str,
    request: P2PDisputeRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Raise a dispute on an order."""
    result = await db.execute(select(P2POrder).where(P2POrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")
    if current_user.id not in (order.buyer_id, order.seller_id):
        raise HTTPException(403, "Not a party to this order")
    if order.status in ("completed", "cancelled"):
        raise HTTPException(400, "Cannot dispute a closed order")

    try:
        db.add(order)
        order.status = "disputed"
        order.dispute_reason = request.reason

        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
    return {"order_id": order_id, "status": "disputed", "message": "Dispute raised. Admin will review within 24h."}


@router.get("/p2p/orders")
async def list_p2p_orders(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Own P2P order history."""
    q = select(P2POrder).where(
        (P2POrder.buyer_id == current_user.id) | (P2POrder.seller_id == current_user.id)
    )
    if status:
        q = q.where(P2POrder.status == status)
    q = q.order_by(P2POrder.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    orders = result.scalars().all()
    return {
        "orders": [
            {
                "id": o.id,
                "offer_id": o.offer_id,
                "buyer_id": o.buyer_id,
                "seller_id": o.seller_id,
                "amount": float(o.amount),
                "rate_ngn": float(o.rate_ngn),
                "fiat_total_ngn": float(o.fiat_total_ngn),
                "status": o.status,
                "my_role": "buyer" if o.buyer_id == current_user.id else "seller",
                "created_at": o.created_at.isoformat(),
                "completed_at": o.completed_at.isoformat() if o.completed_at else None,
            }
            for o in orders
        ],
        "page": page,
        "limit": limit,
    }


@router.get("/p2p/orders/{order_id}")
async def get_p2p_order(
    order_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Single P2P order detail."""
    result = await db.execute(select(P2POrder).where(P2POrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")
    if current_user.id not in (order.buyer_id, order.seller_id):
        raise HTTPException(403, "Not a party to this order")
    return {
        "id": order.id,
        "offer_id": order.offer_id,
        "buyer_id": order.buyer_id,
        "seller_id": order.seller_id,
        "amount": float(order.amount),
        "rate_ngn": float(order.rate_ngn),
        "fiat_total_ngn": float(order.fiat_total_ngn),
        "status": order.status,
        "my_role": "buyer" if order.buyer_id == current_user.id else "seller",
        "dispute_reason": order.dispute_reason,
        "admin_note": order.admin_note,
        "payment_confirmed_at": order.payment_confirmed_at.isoformat() if order.payment_confirmed_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        "created_at": order.created_at.isoformat(),
    }


# ══════════════════════════════════════════════════════════════════════
# SAVINGS VAULTS
# ══════════════════════════════════════════════════════════════════════

@router.get("/vaults")
async def list_vaults(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's active savings vaults."""
    result = await db.execute(
        select(SavingsVault).where(
            SavingsVault.user_id == current_user.id,
            SavingsVault.is_active == True,
        ).order_by(SavingsVault.created_at.desc())
    )
    vaults = result.scalars().all()
    now = datetime.now(timezone.utc)
    return {
        "vaults": [
            {
                "id": v.id,
                "name": v.name,
                "currency": v.currency,
                "amount": float(v.current_balance),
                "lock_period_days": v.lock_period_days,
                "apy_pct": float(v.apy_pct),
                "locked_until": v.locked_until.isoformat() if v.locked_until else None,
                "unlocked": v.locked_until is None or v.locked_until <= now,
                "projected_yield": round(
                    float(v.current_balance) * float(v.apy_pct) / 100 * v.lock_period_days / 365, 8
                ),
                "created_at": v.created_at.isoformat(),
            }
            for v in vaults
        ]
    }


@router.post("/vaults", status_code=201)
async def create_vault(
    request: VaultCreateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a savings vault. Locks funds for chosen period."""
    if request.lock_period_days not in (30, 90, 180, 365):
        raise HTTPException(400, "lock_period_days must be 30, 90, 180, or 365")

    apy_pct = _VAULT_APY.get(request.lock_period_days, Decimal("5.00"))
    amount = Decimal(str(request.amount))
    unlock_date = datetime.now(timezone.utc) + timedelta(days=request.lock_period_days)

    try:
        currency = Currency(request.currency)
    except ValueError:
        raise HTTPException(400, "Invalid currency")

    try:
        service = WalletService(db)
        wallet = await service.get_or_create_wallet(current_user.id)

        attr = f"{currency.value.lower()}_balance"
        current_bal = getattr(wallet, attr, Decimal("0")) or Decimal("0")
        if current_bal < amount:
            raise HTTPException(402, f"Insufficient {currency.value} balance")

        setattr(wallet, attr, current_bal - amount)

        vault = SavingsVault(
            user_id=current_user.id,
            wallet_id=wallet.id,
            name=f"{request.lock_period_days}d {currency.value} Vault",
            vault_type="fixed",
            currency=currency.value,
            current_balance=amount,
            lock_period_days=request.lock_period_days,
            apy_pct=apy_pct,
            locked_until=unlock_date,
            is_active=True,
        )
        db.add(vault)

        ref = f"VAULT-{current_user.id}-{_uuid_mod.uuid4().hex[:8].upper()}"
        db.add(WalletTransaction(
            id=str(_uuid_mod.uuid4()),
            user_id=current_user.id,
            wallet_id=wallet.id,
            type="vault_deposit",
            currency=currency.value,
            amount=amount,
            direction="debit",
            status="confirmed",
            reference=ref,
            description=f"Vault deposit — {request.lock_period_days}d lock",
            processed_at=datetime.now(timezone.utc),
        ))
        await db.flush()

        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
    return {
        "id": vault.id,
        "currency": vault.currency,
        "amount": float(vault.current_balance),
        "lock_period_days": vault.lock_period_days,
        "apy_pct": float(vault.apy_pct),
        "locked_until": vault.locked_until.isoformat(),
        "projected_yield": round(float(amount) * float(apy_pct) / 100 * request.lock_period_days / 365, 8),
    }


@router.post("/vaults/{vault_id}/withdraw")
async def withdraw_vault(
    vault_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw from an unlocked vault."""
    result = await db.execute(select(SavingsVault).where(SavingsVault.id == vault_id))
    vault = result.scalar_one_or_none()
    if not vault or not vault.is_active:
        raise HTTPException(404, "Vault not found")
    if vault.user_id != current_user.id:
        raise HTTPException(403, "Not your vault")

    now = datetime.now(timezone.utc)
    if vault.locked_until and vault.locked_until > now:
        raise HTTPException(400, f"Vault is locked until {vault.locked_until.isoformat()}")

    try:
        currency = Currency(vault.currency)
    except ValueError:
        raise HTTPException(400, "Invalid vault currency")

    yield_amount = Decimal(str(
        round(float(vault.current_balance) * float(vault.apy_pct) / 100 * vault.lock_period_days / 365, 8)
    ))
    total_payout = vault.current_balance + yield_amount

    try:
        service = WalletService(db)
        wallet = await service.get_or_create_wallet(current_user.id)

        attr = f"{currency.value.lower()}_balance"
        setattr(wallet, attr, (getattr(wallet, attr, Decimal("0")) or Decimal("0")) + total_payout)
        vault.is_active = False

        ref = f"VAULT-WD-{_uuid_mod.uuid4().hex[:8].upper()}"
        db.add(WalletTransaction(
            id=str(_uuid_mod.uuid4()),
            user_id=current_user.id,
            wallet_id=wallet.id,
            type="vault_withdrawal",
            currency=currency.value,
            amount=total_payout,
            direction="credit",
            status="confirmed",
            reference=ref,
            description=f"Vault withdrawal (principal + {float(yield_amount):.4f} yield)",
            processed_at=datetime.now(timezone.utc),
        ))

        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
    return {
        "status": "withdrawn",
        "principal": float(vault.current_balance),
        "yield": float(yield_amount),
        "total_payout": float(total_payout),
        "currency": vault.currency,
    }


# ══════════════════════════════════════════════════════════════════════
# REFERRAL EARNINGS
# ══════════════════════════════════════════════════════════════════════

@router.get("/referral/earnings")
async def get_referral_earnings(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Total VITCoin earned from referrals and pending claimable amount."""
    try:
        from app.modules.referral.models import Referral
        ref_result = await db.execute(
            select(Referral).where(Referral.referrer_id == current_user.id)
        )
        referrals = ref_result.scalars().all()
        referral_count = len(referrals)
        total_earned = sum(float(getattr(r, "commission_earned", 0) or 0) for r in referrals)
        total_claimed = sum(float(getattr(r, "commission_claimed", 0) or 0) for r in referrals)
        pending = max(0.0, total_earned - total_claimed)
    except Exception:
        referral_count = 0
        total_earned = 0.0
        pending = 0.0

    tx_result = await db.execute(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0))
        .where(
            WalletTransaction.user_id == current_user.id,
            WalletTransaction.type == "referral_claim",
            WalletTransaction.status == "confirmed",
        )
    )
    already_claimed = float(tx_result.scalar() or 0)

    return {
        "referral_count": referral_count,
        "total_earned_vitcoin": total_earned,
        "pending_claimable": pending,
        "total_claimed": already_claimed,
    }


@router.post("/referral/claim")
async def claim_referral_earnings(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Transfer pending referral earnings to vitcoin_balance."""
    earnings = await get_referral_earnings(current_user=current_user, db=db)
    pending = Decimal(str(earnings["pending_claimable"]))

    if pending <= 0:
        raise HTTPException(400, "No claimable referral earnings")

    try:
        service = WalletService(db)
        wallet = await service.get_or_create_wallet(current_user.id)
        wallet.vitcoin_balance = (wallet.vitcoin_balance or Decimal("0")) + pending

        ref = f"REF-CLAIM-{_uuid_mod.uuid4().hex[:8].upper()}"
        db.add(WalletTransaction(
            id=str(_uuid_mod.uuid4()),
            user_id=current_user.id,
            wallet_id=wallet.id,
            type="referral_claim",
            currency="VITCoin",
            amount=pending,
            direction="credit",
            status="confirmed",
            reference=ref,
            description="Referral earnings claimed",
            processed_at=datetime.now(timezone.utc),
        ))

        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException): raise e
        logger.error(f"Transaction error: {e}")
        raise HTTPException(500, "Internal Server Error")
    return {
        "status": "claimed",
        "amount": float(pending),
        "currency": "VITCoin",
        "reference": ref,
    }


# ══════════════════════════════════════════════════════════════════════
# SUBSCRIPTIONS / PLANS
# ══════════════════════════════════════════════════════════════════════

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
        "VITCoin": plan.price_vitcoin, "VITCOIN": plan.price_vitcoin,
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

    try:
        from app.modules.referral.routes import process_subscription_commission
        await process_subscription_commission(db, current_user.id, Decimal(str(price)))
    except Exception as _re:
        logger.warning(f"Referral subscription commission failed: {_re}")

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


# ══════════════════════════════════════════════════════════════════════
# STATEMENT EXPORT / EXCHANGE RATES
# ══════════════════════════════════════════════════════════════════════

@router.get("/statement/export")
async def export_statement_csv(
    currency: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Download wallet transaction history as CSV."""
    wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
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
            tx.type,
            tx.direction,
            tx.currency,
            float(tx.amount),
            float(tx.fee_amount),
            tx.status,
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
    """Get current exchange rates for all supported currencies."""
    pricing = VITCoinPricingEngine(db)
    vit_prices = await pricing.get_current_price()
    vit_usd = float(vit_prices.get("usd", Decimal("0.10")))

    result_ngn = await db.execute(select(PlatformConfig).where(PlatformConfig.key == "ngn_usd_rate"))
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


# ══════════════════════════════════════════════════════════════════════
# ADMIN KYC
# ══════════════════════════════════════════════════════════════════════

@router.post("/admin/kyc/approve/{user_id}")
async def admin_approve_kyc(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Admin: approve a pending KYC submission."""
    from app.db.models import User as _User

    if getattr(current_user, "role", "viewer") not in ("admin", "superadmin"):
        raise HTTPException(403, "Admin privileges required.")

    user_res = await db.execute(select(_User).where(_User.id == user_id))
    db_user = user_res.scalar_one_or_none()
    if not db_user:
        raise HTTPException(404, "User not found.")

    kyc_status = getattr(db_user, "kyc_status", "none")
    if kyc_status == "approved":
        return {"user_id": user_id, "kyc_status": "approved", "message": "Already approved."}
    if kyc_status not in ("pending",):
        raise HTTPException(400, f"Cannot approve KYC with status '{kyc_status}'.")

    if hasattr(db_user, "kyc_status"):
        db_user.kyc_status = "approved"

    wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = wallet_res.scalar_one_or_none()
    if wallet:
        wallet.kyc_verified = True

    await db.commit()
    return {"user_id": user_id, "kyc_status": "approved", "message": "KYC approved."}


@router.post("/admin/kyc/reject/{user_id}")
async def admin_reject_kyc(
    user_id: int,
    body: Optional[KYCRejectRequest] = Body(default=None),
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

    if hasattr(db_user, "kyc_status"):
        db_user.kyc_status = "rejected"
    await db.commit()
    return {"user_id": user_id, "kyc_status": "rejected", "message": "KYC rejected."}


@router.get("/admin/kyc/pending")
async def admin_list_pending_kyc(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Admin: list users with pending KYC."""
    from app.db.models import User as _User

    if getattr(current_user, "role", "viewer") not in ("admin", "superadmin"):
        raise HTTPException(403, "Admin privileges required.")

    result = await db.execute(
        select(_User).where(_User.kyc_status == "pending").order_by(_User.kyc_submitted_at.asc())
    )
    pending_users = result.scalars().all()
    return {
        "total": len(pending_users),
        "kyc_requests": [
            {
                "user_id": u.id, "username": u.username, "email": u.email,
                "status": getattr(u, "kyc_status", "pending"),
                "full_name": (getattr(u, "kyc_data", None) or {}).get("full_name"),
                "document_type": (getattr(u, "kyc_data", None) or {}).get("document_type"),
                "submitted_at": u.kyc_submitted_at.isoformat() if getattr(u, "kyc_submitted_at", None) else None,
            }
            for u in pending_users
        ],
    }


@router.post("/admin/kyc/{user_id}/approve")
async def admin_approve_kyc_v2(user_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return await admin_approve_kyc(user_id, db=db, current_user=current_user)


@router.post("/admin/kyc/{user_id}/reject")
async def admin_reject_kyc_v2(user_id: int, body: Optional[KYCRejectRequest] = Body(default=None), db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return await admin_reject_kyc(user_id, body=body, db=db, current_user=current_user)


# ══════════════════════════════════════════════════════════════════════
# TELEGRAM / PI / MOMO DEPOSITS (preserved)
# ══════════════════════════════════════════════════════════════════════

class PiDepositRequest(BaseModel):
    amount: float = Field(..., gt=0)
    memo: Optional[str] = None


@router.post("/telegram/stars-invoice")
async def get_telegram_stars_invoice(
    body: StarsInvoiceRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate a Telegram Stars invoice link."""
    if body.stars_amount <= 0:
        raise HTTPException(status_code=400, detail="Stars amount must be positive")
    invoice_link = await create_stars_invoice(current_user.id, body.stars_amount)
    if not invoice_link:
        raise HTTPException(status_code=503, detail="Failed to create Telegram Stars invoice")
    return {"invoice_link": invoice_link}


@router.post("/deposit/pi")
async def initiate_pi_deposit(
    request: PiDepositRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a Pi Network deposit."""
    from app.services.pi_network import is_configured

    service = WalletService(db)
    wallet = await service.get_or_create_wallet(current_user.id)
    ref = f"PI-{current_user.id}-{_uuid_mod.uuid4().hex[:10].upper()}"

    try:
        pending_tx = WalletTransaction(
            id=str(_uuid_mod.uuid4()),
            user_id=current_user.id,
            wallet_id=wallet.id,
            type="deposit",
            currency="PI",
            amount=Decimal(str(request.amount)),
            direction="credit",
            status="pending",
            reference=ref,
            description="Pi Network deposit",
            tx_metadata={"method": "pi_network", "memo": request.memo or f"VIT deposit {ref}"},
        )
        db.add(pending_tx)
        await db.commit()
    except Exception as _e:
        await db.rollback()
        logger.error(f"Failed to record Pi deposit: {_e}")

    return {
        "status": "pending",
        "reference": ref,
        "amount": request.amount,
        "currency": "PI",
        "method": "pi_network",
        "memo": request.memo or f"VIT deposit {ref}",
        "pi_configured": is_configured(),
        "webhook_url": "/api/webhooks/pi",
    }


class MoMoDepositRequest(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field("NGN")
    phone_number: str
    network: Optional[str] = None


@router.post("/deposit/momo")
async def initiate_momo_deposit(
    request: MoMoDepositRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a Mobile Money deposit via Flutterwave."""
    from app.modules.wallet.flutterwave import initiate_momo_deposit as _flw_momo
    from app.config import REPLIT_DEV_DOMAIN, PUBLIC_APP_URL

    currency = request.currency.upper()
    MOMO_CURRENCIES = {"NGN", "GHS", "KES", "UGX", "TZS"}
    if currency not in MOMO_CURRENCIES:
        raise HTTPException(400, f"MoMo deposits only support: {', '.join(MOMO_CURRENCIES)}")

    service = WalletService(db)
    wallet = await service.get_or_create_wallet(current_user.id)
    ref = f"MOMO-{current_user.id}-{_uuid_mod.uuid4().hex[:8].upper()}"
    app_domain = REPLIT_DEV_DOMAIN or PUBLIC_APP_URL or "vitnetwork.app"
    redirect_url = f"https://{app_domain}/wallet?deposit=momo_success&ref={ref}"

    result = await _flw_momo(
        amount=request.amount, currency=currency,
        phone_number=request.phone_number, network=request.network,
        email=current_user.email, reference=ref, redirect_url=redirect_url,
    )

    if result.get("error"):
        return {"status": "error", "message": result["error"], "reference": ref}

    try:
        db.add(WalletTransaction(
            id=str(_uuid_mod.uuid4()),
            user_id=current_user.id,
            wallet_id=wallet.id,
            type="deposit",
            currency=currency,
            amount=Decimal(str(request.amount)),
            direction="credit",
            status="pending",
            reference=ref,
            description="Mobile Money deposit",
            tx_metadata={"method": "flutterwave_momo", "phone_number": request.phone_number},
        ))
        await db.commit()
    except Exception as _e:
        await db.rollback()
        logger.error(f"Failed to record MoMo tx: {_e}")

    return {
        "status": "pending",
        "reference": ref,
        "payment_link": result.get("payment_link"),
        "currency": currency,
        "amount": request.amount,
        "method": "flutterwave_momo",
    }
