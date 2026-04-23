"""Payment provider webhooks — Module B5.

Webhook signature verification:
- Paystack: HMAC-SHA512 of raw body with PAYSTACK_WEBHOOK_SECRET
- Stripe:   Stripe-Signature header verified via STRIPE_WEBHOOK_SECRET
- USDT:     Internal listener (trust via network policy)
- Pi:       Pi Network payment approval
"""

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.modules.wallet.models import WalletTransaction, Wallet

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)

PAYSTACK_WEBHOOK_SECRET = os.getenv("PAYSTACK_WEBHOOK_SECRET", "")
STRIPE_WEBHOOK_SECRET   = os.getenv("STRIPE_WEBHOOK_SECRET", "")
USDT_MIN_CONFIRMATIONS  = int(os.getenv("USDT_MIN_CONFIRMATIONS", "3"))


async def _credit_wallet_by_reference(reference: str) -> bool:
    """Find a pending transaction by reference and credit the wallet."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WalletTransaction).where(WalletTransaction.reference == reference)
        )
        tx = result.scalar_one_or_none()
        if not tx or tx.status == "confirmed":
            return False

        wallet_result = await db.execute(select(Wallet).where(Wallet.id == tx.wallet_id))
        wallet = wallet_result.scalar_one_or_none()
        if not wallet:
            return False

        balance_attr = f"{tx.currency.lower()}_balance"
        current = getattr(wallet, balance_attr, 0) or 0
        setattr(wallet, balance_attr, current + tx.amount)
        tx.status = "confirmed"
        tx.processed_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info(f"Webhook credited {tx.amount} {tx.currency} to wallet {tx.wallet_id} (ref={reference})")
        return True


async def _activate_subscription(user_id: int, plan: str, billing: str) -> bool:
    """
    Grant a subscription tier to a user after successful Stripe payment.
    Updates User.subscription_tier and sends an in-app notification.
    """
    from datetime import timedelta
    from app.db.models import User
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                logger.warning(f"_activate_subscription: user {user_id} not found")
                return False

            old_tier = getattr(user, "subscription_tier", "viewer")
            user.subscription_tier = plan

            # Also update/create a UserSubscription record for API-key-based gating
            from app.db.models import UserSubscription
            now = datetime.now(timezone.utc)
            days = 365 if billing == "yearly" else 30
            # Use a stable hash of user_id as the "api_key" for webhook-activated subs
            import hashlib
            pseudo_key_hash = hashlib.sha256(f"stripe_user_{user_id}".encode()).hexdigest()
            sub_result = await db.execute(
                select(UserSubscription).where(UserSubscription.api_key_hash == pseudo_key_hash)
            )
            sub = sub_result.scalar_one_or_none()
            if sub:
                sub.plan_name = plan
                sub.status = "active"
                sub.current_period_start = now
                sub.current_period_end = now + timedelta(days=days)
            else:
                sub = UserSubscription(
                    api_key_hash=pseudo_key_hash,
                    plan_name=plan,
                    status="active",
                    current_period_start=now,
                    current_period_end=now + timedelta(days=days),
                )
                db.add(sub)

            await db.commit()

            # Send in-app notification
            try:
                from app.modules.notifications.service import NotificationService
                await NotificationService.create(
                    db=db,
                    user_id=user_id,
                    type="subscription_upgrade",
                    title=f"Plan Upgraded to {plan.capitalize()}",
                    body=f"Your VIT {plan.capitalize()} plan is now active. Enjoy your new features!",
                    channel="in_app",
                )
            except Exception as ne:
                logger.warning(f"Notification after subscription activation failed: {ne}")

            logger.info(f"User {user_id} upgraded {old_tier} → {plan} (billing={billing})")

            # ── Credit referrer commission (v4.5) ────────────────────────
            # If the new subscriber used a referral code, award the referrer
            # a commission in VITCoin (5 VIT for analyst, 15 for pro/validator).
            if plan in ("analyst", "pro", "validator") and old_tier in ("viewer", "free", None):
                try:
                    from app.modules.referral.models import ReferralUse
                    from app.modules.wallet.models import Wallet
                    from decimal import Decimal

                    COMMISSION = {"analyst": Decimal("5"), "pro": Decimal("15"), "validator": Decimal("20")}
                    commission = COMMISSION.get(plan, Decimal("5"))

                    ref_use_res = await db.execute(
                        select(ReferralUse).where(ReferralUse.referee_id == user_id)
                    )
                    ref_use = ref_use_res.scalar_one_or_none()
                    if ref_use and ref_use.referrer_id:
                        referrer_wallet_res = await db.execute(
                            select(Wallet).where(Wallet.user_id == ref_use.referrer_id)
                        )
                        referrer_wallet = referrer_wallet_res.scalar_one_or_none()
                        if referrer_wallet:
                            referrer_wallet.vitcoin_balance = (referrer_wallet.vitcoin_balance or Decimal("0")) + commission
                            await db.commit()
                            logger.info(
                                f"Referral commission: {commission} VIT credited to user {ref_use.referrer_id} "
                                f"(referee {user_id} upgraded to {plan})"
                            )
                            try:
                                from app.modules.notifications.service import NotificationService as _NS
                                await _NS.create(
                                    db=db,
                                    user_id=ref_use.referrer_id,
                                    type="referral_reward",
                                    title="Referral Commission Earned!",
                                    body=f"You earned {commission} VIT — your referral just upgraded to {plan.capitalize()}!",
                                    channel="in_app",
                                )
                            except Exception:
                                pass
                except Exception as re:
                    logger.warning(f"Referral commission failed (non-fatal): {re}")

            return True
    except Exception as e:
        logger.error(f"_activate_subscription failed for user {user_id}: {e}", exc_info=True)
        return False


async def _mark_withdrawal_processed(reference: str) -> bool:
    """Mark a withdrawal transaction as processed."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WalletTransaction).where(WalletTransaction.reference == reference)
        )
        tx = result.scalar_one_or_none()
        if not tx:
            return False
        tx.status = "confirmed"
        tx.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return True


# ── Paystack ───────────────────────────────────────────────────────────

@router.post("/paystack")
async def paystack_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")
    secret = os.getenv("PAYSTACK_WEBHOOK_SECRET", "")

    if secret:
        computed = hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()
        if not hmac.compare_digest(computed, signature):
            raise HTTPException(400, "Invalid Paystack signature")

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    event = payload.get("event", "")

    if event == "charge.success":
        reference = payload.get("data", {}).get("reference", "")
        await _credit_wallet_by_reference(reference)

    elif event == "transfer.success":
        reference = payload.get("data", {}).get("reference", "")
        await _mark_withdrawal_processed(reference)

    return {"status": "ok"}


# ── Stripe ─────────────────────────────────────────────────────────────

def _verify_stripe_signature(body: bytes, sig_header: str, secret: str) -> bool:
    """
    Verify Stripe webhook signature (Stripe-Signature header).
    Stripe format: t=<timestamp>,v1=<signature>
    Ref: https://stripe.com/docs/webhooks/signatures
    """
    if not secret or not sig_header:
        return not bool(secret)  # allow-through when no secret configured
    try:
        parts = {}
        for part in sig_header.split(","):
            k, v = part.split("=", 1)
            parts[k.strip()] = v.strip()
        timestamp = parts.get("t", "")
        v1_sig = parts.get("v1", "")
        if not timestamp or not v1_sig:
            return False
        # Reject stale webhooks (> 5 minutes old)
        if abs(time.time() - int(timestamp)) > 300:
            logger.warning("Stripe webhook: timestamp too old (possible replay)")
            return False
        signed_payload = f"{timestamp}.".encode() + body
        expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, v1_sig)
    except Exception as exc:
        logger.warning(f"Stripe signature verification error: {exc}")
        return False


@router.post("/stripe", summary="Stripe payment webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(default=None, alias="stripe-signature"),
):
    body = await request.body()

    if STRIPE_WEBHOOK_SECRET:
        if not stripe_signature or not _verify_stripe_signature(body, stripe_signature, STRIPE_WEBHOOK_SECRET):
            logger.warning("Stripe webhook: invalid signature rejected")
            raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = payload.get("type", "")
    obj = payload.get("data", {}).get("object", {})
    logger.info(f"Stripe webhook event: {event_type}")

    if event_type == "payment_intent.succeeded":
        reference = obj.get("metadata", {}).get("reference", obj.get("id", ""))
        credited = await _credit_wallet_by_reference(reference)
        return {"status": "ok", "credited": credited}

    if event_type in ("charge.succeeded", "checkout.session.completed"):
        metadata = obj.get("metadata", {})
        reference = metadata.get("reference", obj.get("id", ""))
        credited = await _credit_wallet_by_reference(reference)

        # If this is a VIT subscription checkout, also activate the plan
        vit_plan    = metadata.get("vit_plan", "")
        vit_user_id = metadata.get("vit_user_id", "")
        vit_billing = metadata.get("vit_billing", "monthly")
        if vit_plan and vit_user_id:
            activated = await _activate_subscription(int(vit_user_id), vit_plan, vit_billing)
            logger.info(f"Stripe subscription activation: user={vit_user_id} plan={vit_plan} activated={activated}")

        return {"status": "ok", "credited": credited}

    if event_type == "payout.paid":
        processed = await _mark_withdrawal_processed(obj.get("id", ""))
        return {"status": "ok", "processed": processed}

    if event_type == "payment_intent.payment_failed":
        logger.warning(f"Stripe payment failed: {obj.get('id', '')}")
        return {"status": "ok", "note": "payment_failed logged"}

    return {"status": "ok", "event": event_type, "handled": False}


# ── USDT (internal listener) ───────────────────────────────────────────

class USDTWebhookBody(BaseModel):
    address: str
    amount: float
    tx_hash: str
    confirmations: int


@router.post("/usdt")
async def usdt_webhook(body: USDTWebhookBody):
    min_conf = int(os.getenv("USDT_MIN_CONFIRMATIONS", "3"))
    if body.confirmations < min_conf:
        return {
            "status": "waiting_confirmations",
            "required": min_conf,
            "current": body.confirmations,
        }

    credited = await _credit_wallet_by_reference(body.tx_hash)
    return {"status": "confirmed" if credited else "not_found"}


# ── Pi Network ─────────────────────────────────────────────────────────

class PiWebhookBody(BaseModel):
    payment_id: str
    approved: bool = False


@router.post("/pi")
async def pi_webhook(body: PiWebhookBody):
    if not body.approved:
        return {"status": "not_approved"}

    credited = await _credit_wallet_by_reference(body.payment_id)
    return {"status": "confirmed" if credited else "not_found"}
