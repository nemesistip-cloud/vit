# app/modules/wallet/p2p_routes.py
"""Activated P2P Exchange routes — decoupled and enhanced."""

import logging
import uuid as _uuid_mod
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, Body, Header
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.api.deps import get_current_user
from app.core.errors import AppError
from app.core.cache import cache
from app.modules.wallet.models import (
    P2POffer, P2POrder, Wallet, WalletTransaction, Currency
)
from app.modules.wallet.services import WalletService
from app.modules.wallet.pricing_engine import VITCoinPricingEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wallet/p2p", tags=["P2P Exchange"])

# ── Request Schemas ───────────────────────────────────────────────────

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

# ── Idempotency helper ─────────────────────────────────────────────────

async def _check_idempotency(key: Optional[str], user_id: int) -> Optional[dict]:
    if not key: return None
    return await cache.get(f"p2p:idempotency:{user_id}:{key}")

async def _store_idempotency(key: Optional[str], user_id: int, result: dict) -> None:
    if not key: return
    await cache.set(f"p2p:idempotency:{user_id}:{key}", result, ttl=86400)

# ── Endpoints ──────────────────────────────────────────────────────────

@router.get("/offers")
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

@router.post("/offers", status_code=201)
async def create_p2p_offer(
    request: P2POfferCreateRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a P2P offer. Escrows VITCoin immediately for sell offers."""
    cached = await _check_idempotency(x_idempotency_key, current_user.id)
    if cached: return cached

    if request.offer_type not in ("buy", "sell"):
        raise AppError("offer_type must be buy or sell", code="invalid_offer_type")
    if request.min_order > request.max_order:
        raise AppError("min_order must be ≤ max_order", code="invalid_order_range")
    if request.max_order > request.amount:
        raise AppError("max_order must be ≤ offer amount", code="invalid_max_order")

    async with db.begin():
        service = WalletService(db)
        wallet = await service.get_or_create_wallet(current_user.id)

        escrowed = Decimal("0")
        if request.offer_type == "sell":
            amount = Decimal(str(request.amount))
            if (wallet.vitcoin_balance or Decimal("0")) < amount:
                raise AppError("Insufficient VITCoin balance for escrow", status_code=402, code="insufficient_balance")

            wallet.vitcoin_balance -= amount
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

        res = {
            "id": offer.id,
            "status": offer.status,
            "offer_type": offer.offer_type,
            "amount": float(offer.total_amount)
        }
        await _store_idempotency(x_idempotency_key, current_user.id, res)
        return res

@router.delete("/offers/{offer_id}")
async def cancel_p2p_offer(
    offer_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel own P2P offer and release escrow if sell offer."""
    async with db.begin():
        result = await db.execute(select(P2POffer).where(P2POffer.id == offer_id))
        offer = result.scalar_one_or_none()
        if not offer:
            raise AppError("Offer not found", status_code=404, code="not_found")
        if offer.user_id != current_user.id:
            raise AppError("Not your offer", status_code=403, code="forbidden")
        if offer.status not in ("active", "paused"):
            raise AppError("Offer cannot be cancelled in its current state", code="invalid_state")

        offer.status = "cancelled"
        if offer.offer_type == "sell" and offer.escrowed_amount > 0:
            service = WalletService(db)
            wallet = await service.get_or_create_wallet(current_user.id)
            wallet.vitcoin_balance += offer.escrowed_amount

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

    return {"status": "cancelled", "offer_id": offer_id}

@router.post("/orders", status_code=201)
async def create_p2p_order(
    request: P2POrderCreateRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a trade against a P2P offer."""
    cached = await _check_idempotency(x_idempotency_key, current_user.id)
    if cached: return cached

    async with db.begin():
        result = await db.execute(select(P2POffer).where(P2POffer.id == request.offer_id))
        offer = result.scalar_one_or_none()
        if not offer or offer.status != "active":
            raise AppError("Offer not found or inactive", status_code=404, code="not_found")
        if offer.user_id == current_user.id:
            raise AppError("Cannot trade against your own offer", code="invalid_trade")

        amount = Decimal(str(request.amount))
        if amount < offer.min_order or amount > offer.max_order:
            raise AppError(f"Amount must be between {offer.min_order} and {offer.max_order}", code="invalid_amount")
        if amount > offer.available_amount:
            raise AppError("Requested amount exceeds offer availability", code="insufficient_availability")

        fiat_total = amount * offer.rate_ngn

        # Determine Buyer/Seller
        # If Maker is SELLING, Maker is Seller, Taker is Buyer.
        # If Maker is BUYING, Maker is Buyer, Taker is Seller.
        if offer.offer_type == "sell":
            seller_id = offer.user_id
            buyer_id = current_user.id
        else:
            seller_id = current_user.id
            buyer_id = offer.user_id

            # FIX: Taker-Sell Scenario. We MUST escrow from the Taker (current_user)
            service = WalletService(db)
            taker_wallet = await service.get_or_create_wallet(current_user.id)
            if taker_wallet.vitcoin_balance < amount:
                raise AppError("Insufficient VITCoin balance to fulfill this buy offer", status_code=402, code="insufficient_balance")

            taker_wallet.vitcoin_balance -= amount
            # Note: For Buy offers, we don't necessarily have a pre-existing escrow column update
            # in the same way because Maker didn't provide VIT.
            # We'll use the Order itself as the escrow record.
            db.add(WalletTransaction(
                id=str(_uuid_mod.uuid4()),
                user_id=current_user.id,
                wallet_id=taker_wallet.id,
                type="p2p_escrow",
                currency="VITCoin",
                amount=amount,
                direction="debit",
                status="confirmed",
                reference=f"P2P-T-ESC-{_uuid_mod.uuid4().hex[:8].upper()}",
                description="P2P taker escrow for buy offer",
                processed_at=datetime.now(timezone.utc),
            ))

        offer.available_amount -= amount

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
        await db.flush()

        res = {
            "id": order.id,
            "status": order.status,
            "buyer_id": buyer_id,
            "seller_id": seller_id,
            "amount": float(amount)
        }
        await _store_idempotency(x_idempotency_key, current_user.id, res)
        return res

@router.post("/orders/{order_id}/confirm-payment")
async def p2p_confirm_payment(
    order_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Buyer confirms fiat has been sent."""
    async with db.begin():
        result = await db.execute(select(P2POrder).where(P2POrder.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            raise AppError("Order not found", status_code=404, code="not_found")
        if order.buyer_id != current_user.id:
            raise AppError("Only the buyer can confirm payment", status_code=403, code="forbidden")
        if order.status != "pending":
            raise AppError(f"Order is already {order.status}", code="invalid_state")

        order.status = "payment_sent"
        order.payment_confirmed_at = datetime.now(timezone.utc)

    return {"order_id": order_id, "status": "payment_sent"}

@router.post("/orders/{order_id}/release")
async def p2p_release_escrow(
    order_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Seller releases escrowed VITCoin to buyer."""
    async with db.begin():
        result = await db.execute(select(P2POrder).where(P2POrder.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            raise AppError("Order not found", status_code=404, code="not_found")
        if order.seller_id != current_user.id:
            raise AppError("Only the seller can release escrow", status_code=403, code="forbidden")
        if order.status != "payment_sent":
            raise AppError("Order must be in payment_sent state", code="invalid_state")

        service = WalletService(db)
        buyer_wallet = await service.get_or_create_wallet(order.buyer_id)

        ref = f"P2P-REL-{_uuid_mod.uuid4().hex[:8].upper()}"
        buyer_wallet.vitcoin_balance += order.amount

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

    return {"order_id": order_id, "status": "completed", "amount_released": float(order.amount)}

@router.post("/orders/{order_id}/dispute")
async def p2p_raise_dispute(
    order_id: str,
    request: P2PDisputeRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Raise a dispute on an order."""
    async with db.begin():
        result = await db.execute(select(P2POrder).where(P2POrder.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            raise AppError("Order not found", status_code=404, code="not_found")
        if current_user.id not in (order.buyer_id, order.seller_id):
            raise AppError("Not a party to this order", status_code=403, code="forbidden")
        if order.status in ("completed", "cancelled"):
            raise AppError("Cannot dispute a closed order", code="invalid_state")

        order.status = "disputed"
        order.dispute_reason = request.reason

    return {"order_id": order_id, "status": "disputed", "message": "Dispute raised. Admin will review."}

@router.get("/orders")
async def list_p2p_orders(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Own P2P order history."""
    q = select(P2POrder).where(
        or_(P2POrder.buyer_id == current_user.id, P2POrder.seller_id == current_user.id)
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

@router.get("/orders/{order_id}")
async def get_p2p_order(
    order_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Single P2P order detail."""
    result = await db.execute(select(P2POrder).where(P2POrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise AppError("Order not found", status_code=404, code="not_found")
    if current_user.id not in (order.buyer_id, order.seller_id):
        raise AppError("Not a party to this order", status_code=403, code="forbidden")

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
        "payment_confirmed_at": order.payment_confirmed_at.isoformat() if order.payment_confirmed_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        "created_at": order.created_at.isoformat(),
    }
