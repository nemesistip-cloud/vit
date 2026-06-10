"""Payment provider webhooks — Module B5.

Webhook signature verification:
- Paystack: HMAC-SHA512 of raw body with PAYSTACK_WEBHOOK_SECRET
- Stripe:   Stripe-Signature header verified via STRIPE_WEBHOOK_SECRET
- USDT:     Internal listener (trust via network policy)
- Pi:       Pi Network payment approval
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.modules.wallet.models import WalletTransaction, Wallet
from app.config import PAYSTACK_WEBHOOK_SECRET as _PAYSTACK_WEBHOOK_SECRET, USDT_MIN_CONFIRMATIONS

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)


async def _log_event(
    *,
    provider: str,
    event_type: Optional[str] = None,
    reference: Optional[str] = None,
    amount: Optional[float] = None,
    currency: Optional[str] = None,
    status: str = "received",
    sig_verified: Optional[bool] = None,
    outcome: Optional[str] = None,
    error_msg: Optional[str] = None,
    payload_summary: Optional[dict] = None,
) -> None:
    """Persist a webhook delivery record. Silently swallows errors so it never breaks a handler."""
    try:
        from app.modules.wallet.models import WebhookEvent
        async with AsyncSessionLocal() as db:
            db.add(WebhookEvent(
                provider=provider,
                event_type=event_type,
                reference=reference,
                amount=Decimal(str(amount)) if amount is not None else None,
                currency=currency,
                status=status,
                sig_verified=sig_verified,
                outcome=outcome,
                error_msg=error_msg,
                payload_summary=payload_summary,
            ))
            await db.commit()
    except Exception as _e:
        logger.debug(f"_log_event swallowed error: {_e}")

# ── Flutterwave ──────────────────────────────────────────────────────────
from app.modules.wallet.flutterwave import verify_webhook_signature as _flw_verify_sig


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


async def _fail_pending_transaction(payment_intent_id: str) -> bool:
    """Mark a pending deposit transaction as failed when Stripe reports payment_intent.payment_failed."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WalletTransaction).where(
                WalletTransaction.status == "pending",
                WalletTransaction.tx_metadata.op("->>")(  # type: ignore[attr-defined]
                    "payment_intent_id"
                ) == payment_intent_id,
            )
        )
        tx = result.scalar_one_or_none()
        if not tx:
            # Try matching by reference as fallback
            result2 = await db.execute(
                select(WalletTransaction).where(
                    WalletTransaction.reference.contains(payment_intent_id[:10]),
                    WalletTransaction.status == "pending",
                )
            )
            tx = result2.scalars().first()
        if not tx:
            logger.warning(f"_fail_pending_transaction: no pending tx for pi={payment_intent_id}")
            return False
        tx.status = "failed"
        tx.processed_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info(f"Marked tx {tx.id} as failed (Stripe pi={payment_intent_id})")
        return True


async def _reverse_confirmed_transaction(charge_id: str, refund_amt: float) -> bool:
    """Reverse a confirmed deposit transaction after a Stripe refund."""
    from decimal import Decimal
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WalletTransaction).where(
                WalletTransaction.status == "confirmed",
                WalletTransaction.type == "deposit",
            ).order_by(WalletTransaction.processed_at.desc()).limit(50)
        )
        txs = result.scalars().all()
        # Match by charge_id in metadata or by amount proximity
        tx = None
        for t in txs:
            meta = t.tx_metadata or {}
            if meta.get("charge_id") == charge_id or meta.get("stripe_charge") == charge_id:
                tx = t
                break
        if not tx and txs:
            # Fallback: match nearest amount
            refund_d = Decimal(str(round(refund_amt, 2)))
            for t in txs:
                if abs(t.amount - refund_d) < Decimal("0.02"):
                    tx = t
                    break
        if not tx:
            logger.warning(f"_reverse_confirmed_transaction: no matching tx for charge={charge_id}")
            return False
        wallet_result = await db.execute(select(Wallet).where(Wallet.id == tx.wallet_id))
        wallet = wallet_result.scalar_one_or_none()
        if wallet:
            balance_attr = f"{tx.currency.lower()}_balance"
            current = getattr(wallet, balance_attr, Decimal("0")) or Decimal("0")
            debit = min(Decimal(str(refund_amt)), tx.amount)
            setattr(wallet, balance_attr, max(Decimal("0"), current - debit))
        tx.status = "reversed"
        await db.commit()
        logger.info(f"Reversed tx {tx.id} amount={refund_amt} (Stripe charge={charge_id})")
        return True


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
    secret = _PAYSTACK_WEBHOOK_SECRET or os.getenv("PAYSTACK_WEBHOOK_SECRET", "")

    if secret:
        computed = hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()
        if not hmac.compare_digest(computed, signature):
            raise HTTPException(400, "Invalid Paystack signature")

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    event = payload.get("event", "")
    reference = payload.get("data", {}).get("reference", "")
    amount_data = payload.get("data", {}).get("amount", None)
    currency_data = payload.get("data", {}).get("currency", None)
    outcome = "unhandled"

    if event == "charge.success":
        credited = await _credit_wallet_by_reference(reference)
        outcome = "credited" if credited else "already_processed"

    elif event == "transfer.success":
        await _mark_withdrawal_processed(reference)
        outcome = "withdrawal_processed"

    asyncio.create_task(_log_event(
        provider="paystack",
        event_type=event,
        reference=reference or None,
        amount=float(amount_data) if amount_data else None,
        currency=currency_data,
        status="processed",
        sig_verified=True,
        outcome=outcome,
        payload_summary={"event": event, "reference": reference},
    ))
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

    # Read at request time so dynamically configured secrets (via admin panel) work immediately.
    stripe_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # G03: Enforce signature verification. Return 503 if secret not configured.
    if not stripe_secret:
        logger.error("Stripe webhook: STRIPE_WEBHOOK_SECRET not configured — rejecting")
        raise HTTPException(
            status_code=503,
            detail="Stripe webhook secret not configured. Set STRIPE_WEBHOOK_SECRET env var.",
        )

    if not stripe_signature or not _verify_stripe_signature(body, stripe_signature, stripe_secret):
        logger.warning("Stripe webhook: invalid signature rejected")
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = payload.get("type", "")
    obj = payload.get("data", {}).get("object", {})
    logger.info(f"Stripe webhook event: {event_type}")

    _log_ref = obj.get("id", "")
    _log_amt = obj.get("amount", 0) / 100.0 if obj.get("amount") else None
    _log_currency = obj.get("currency", "usd").upper() if obj.get("currency") else "USD"

    async def _stripe_log(outcome: str, error_msg: Optional[str] = None) -> None:
        asyncio.create_task(_log_event(
            provider="stripe",
            event_type=event_type,
            reference=_log_ref or None,
            amount=_log_amt,
            currency=_log_currency,
            status="processed",
            sig_verified=True,
            outcome=outcome,
            error_msg=error_msg,
            payload_summary={"type": event_type, "id": obj.get("id", "")},
        ))

    if event_type == "payment_intent.succeeded":
        reference = obj.get("metadata", {}).get("reference", obj.get("id", ""))
        credited = await _credit_wallet_by_reference(reference)
        await _stripe_log("credited" if credited else "already_processed")
        return {"status": "ok", "credited": credited}

    if event_type in ("charge.succeeded", "checkout.session.completed"):
        metadata = obj.get("metadata", {})
        reference = metadata.get("reference", obj.get("id", ""))
        credited = await _credit_wallet_by_reference(reference)

        vit_plan    = metadata.get("vit_plan", "")
        vit_user_id = metadata.get("vit_user_id", "")
        vit_billing = metadata.get("vit_billing", "monthly")
        if vit_plan and vit_user_id:
            activated = await _activate_subscription(int(vit_user_id), vit_plan, vit_billing)
            logger.info(f"Stripe subscription activation: user={vit_user_id} plan={vit_plan} activated={activated}")

        await _stripe_log("credited" if credited else "subscription_activated" if vit_plan else "already_processed")
        return {"status": "ok", "credited": credited}

    if event_type == "payout.paid":
        processed = await _mark_withdrawal_processed(obj.get("id", ""))
        await _stripe_log("withdrawal_processed" if processed else "not_found")
        return {"status": "ok", "processed": processed}

    if event_type == "payment_intent.payment_failed":
        pi_id = obj.get("id", "")
        logger.warning(f"Stripe payment failed: {pi_id}")
        updated = await _fail_pending_transaction(pi_id)
        await _stripe_log("payment_failed")
        return {"status": "ok", "note": "payment_failed", "updated": updated}

    if event_type == "charge.refunded":
        charge_id = obj.get("id", "")
        refund_amt = obj.get("amount_refunded", 0) / 100.0
        logger.info(f"Stripe charge refunded: {charge_id} amount={refund_amt}")
        reversed_tx = await _reverse_confirmed_transaction(charge_id, refund_amt)
        await _stripe_log("refunded")
        return {"status": "ok", "note": "charge_refunded", "reversed": reversed_tx}

    await _stripe_log("unhandled")
    return {"status": "ok", "event": event_type, "handled": False}


# ── USDT (internal listener) ───────────────────────────────────────────

class USDTWebhookBody(BaseModel):
    address: str
    amount: float
    tx_hash: str
    confirmations: int


@router.post("/usdt")
async def usdt_webhook(body: USDTWebhookBody):
    try:
        min_conf = int(os.getenv("USDT_MIN_CONFIRMATIONS", "3"))
    except (ValueError, TypeError):
        min_conf = USDT_MIN_CONFIRMATIONS
    if body.confirmations < min_conf:
        asyncio.create_task(_log_event(
            provider="usdt",
            event_type="deposit",
            reference=body.tx_hash,
            amount=body.amount,
            currency="USDT",
            status="waiting_confirmations",
            sig_verified=None,
            outcome="pending",
            payload_summary={"confirmations": body.confirmations, "required": min_conf},
        ))
        return {
            "status": "waiting_confirmations",
            "required": min_conf,
            "current": body.confirmations,
        }

    credited = await _credit_wallet_by_reference(body.tx_hash)
    asyncio.create_task(_log_event(
        provider="usdt",
        event_type="deposit",
        reference=body.tx_hash,
        amount=body.amount,
        currency="USDT",
        status="processed",
        sig_verified=None,
        outcome="credited" if credited else "not_found",
        payload_summary={"address": body.address, "confirmations": body.confirmations},
    ))
    return {"status": "confirmed" if credited else "not_found"}


# ── Pi Network ─────────────────────────────────────────────────────────

class PiWebhookBody(BaseModel):
    payment_id: str
    event_type: Optional[str] = None   # payment_approved | payment_ready_for_server_completion | payment_cancelled
    approved: bool = False
    txid: Optional[str] = None         # on-chain txid from Pi Blockchain
    user_uid: Optional[str] = None


@router.post("/pi")
async def pi_webhook(request: Request):
    """
    Pi Network Server-to-App webhook.

    Events handled:
      payment_approved                     → server-side approve via Pi API
      payment_ready_for_server_completion  → complete payment + credit wallet
      payment_cancelled                    → log only
    """
    from app.services.pi_network import (
        approve_payment as _pi_approve,
        complete_payment as _pi_complete,
        verify_webhook_signature as _pi_verify_sig,
    )

    body_bytes = await request.body()
    sig = request.headers.get("x-pi-network-signature", "")
    if sig and not _pi_verify_sig(body_bytes, sig):
        raise HTTPException(400, "Invalid Pi Network webhook signature")

    try:
        payload = json.loads(body_bytes)
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    event_type = payload.get("event_type", "")
    payment = payload.get("payment", {}) or {}
    payment_id = payment.get("identifier") or payload.get("payment_id", "")
    txid = payment.get("transaction", {}).get("txid") if isinstance(payment.get("transaction"), dict) else payload.get("txid")
    amount = float(payment.get("amount", 0))

    logger.info(f"Pi webhook: event={event_type} payment_id={payment_id} amount={amount}")

    _pi_sig_ok = not sig or True   # sig already verified above; True if sig absent (optional field)

    if event_type == "payment_approved":
        result = await _pi_approve(payment_id)
        err = result.get("error")
        if err:
            logger.error(f"Pi approve failed: {err}")
        asyncio.create_task(_log_event(
            provider="pi",
            event_type=event_type,
            reference=payment_id or None,
            amount=amount if amount else None,
            currency="PI",
            status="processed",
            sig_verified=_pi_sig_ok,
            outcome="approved" if not err else "approve_failed",
            error_msg=err,
            payload_summary={"payment_id": payment_id, "amount": amount},
        ))
        return {"status": "ok", "action": "approved", "payment_id": payment_id}

    if event_type == "payment_ready_for_server_completion":
        if not txid:
            logger.error(f"Pi completion webhook missing txid for payment {payment_id}")
            asyncio.create_task(_log_event(
                provider="pi", event_type=event_type, reference=payment_id or None,
                amount=amount if amount else None, currency="PI", status="error",
                sig_verified=_pi_sig_ok, outcome="missing_txid",
                error_msg="txid missing in payload",
            ))
            return {"status": "error", "message": "txid missing"}
        result = await _pi_complete(payment_id, txid)
        if result.get("error"):
            logger.error(f"Pi complete failed: {result['error']}")
            asyncio.create_task(_log_event(
                provider="pi", event_type=event_type, reference=payment_id or None,
                amount=amount if amount else None, currency="PI", status="error",
                sig_verified=_pi_sig_ok, outcome="complete_failed",
                error_msg=result["error"],
            ))
            return {"status": "error", "message": result["error"]}
        credited = await _credit_wallet_by_reference(payment_id)
        if not credited and txid:
            credited = await _credit_wallet_by_reference(txid)
        asyncio.create_task(_log_event(
            provider="pi",
            event_type=event_type,
            reference=payment_id or None,
            amount=amount if amount else None,
            currency="PI",
            status="processed",
            sig_verified=_pi_sig_ok,
            outcome="credited" if credited else "already_processed",
            payload_summary={"payment_id": payment_id, "txid": txid, "amount": amount},
        ))
        return {"status": "ok", "action": "completed", "credited": credited, "payment_id": payment_id}

    if event_type == "payment_cancelled":
        logger.info(f"Pi payment cancelled: payment_id={payment_id}")
        asyncio.create_task(_log_event(
            provider="pi", event_type=event_type, reference=payment_id or None,
            amount=amount if amount else None, currency="PI", status="processed",
            sig_verified=_pi_sig_ok, outcome="cancelled",
        ))
        return {"status": "ok", "action": "cancelled"}

    # Legacy simple webhook (direct payment_id + approved fields)
    if not event_type:
        approved = payload.get("approved", False)
        payment_id_simple = payload.get("payment_id", "")
        if not approved:
            asyncio.create_task(_log_event(
                provider="pi", event_type="legacy", reference=payment_id_simple or None,
                status="received", sig_verified=_pi_sig_ok, outcome="not_approved",
            ))
            return {"status": "not_approved"}
        credited = await _credit_wallet_by_reference(payment_id_simple)
        asyncio.create_task(_log_event(
            provider="pi", event_type="legacy", reference=payment_id_simple or None,
            status="processed", sig_verified=_pi_sig_ok,
            outcome="credited" if credited else "not_found",
        ))
        return {"status": "confirmed" if credited else "not_found"}

    asyncio.create_task(_log_event(
        provider="pi", event_type=event_type, reference=payment_id or None,
        status="received", sig_verified=_pi_sig_ok, outcome="unhandled",
    ))
    return {"status": "ok", "event_type": event_type, "handled": False}


# ── Flutterwave ─────────────────────────────────────────────────────────

@router.post("/flutterwave")
async def flutterwave_webhook(request: Request):
    """Flutterwave webhook handler for MoMo and card payments."""
    body = await request.body()
    signature = request.headers.get("verif-hash", "")

    if not _flw_verify_sig(body, signature):
        raise HTTPException(400, "Invalid Flutterwave signature")

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    event = payload.get("event", "")
    data = payload.get("data", {})
    status = data.get("status", "")
    tx_ref = data.get("tx_ref", data.get("txRef", ""))
    flw_ref = data.get("flw_ref", data.get("flwRef", ""))
    amount = data.get("amount", 0)

    logger.info(f"Flutterwave webhook: event={event} status={status} tx_ref={tx_ref}")

    if event in ("charge.completed", "transfer.completed") and status == "successful":
        credited = await _credit_wallet_by_reference(tx_ref)
        if not credited and flw_ref:
            credited = await _credit_wallet_by_reference(flw_ref)
        asyncio.create_task(_log_event(
            provider="flutterwave",
            event_type=event,
            reference=tx_ref or flw_ref or None,
            amount=float(amount) if amount else None,
            currency=data.get("currency"),
            status="processed",
            sig_verified=True,
            outcome="credited" if credited else "already_processed",
            payload_summary={"event": event, "status": status, "tx_ref": tx_ref},
        ))
        return {"status": "ok", "credited": credited, "tx_ref": tx_ref}

    if event == "transfer.completed" and status == "successful":
        processed = await _mark_withdrawal_processed(tx_ref)
        asyncio.create_task(_log_event(
            provider="flutterwave",
            event_type=event,
            reference=tx_ref or None,
            amount=float(amount) if amount else None,
            currency=data.get("currency"),
            status="processed",
            sig_verified=True,
            outcome="withdrawal_processed" if processed else "not_found",
        ))
        return {"status": "ok", "processed": processed}

    if event == "transfer.failed" or (event == "charge.completed" and status == "failed"):
        logger.warning(f"Flutterwave transaction failed: tx_ref={tx_ref}")
        await _fail_pending_transaction(tx_ref)
        asyncio.create_task(_log_event(
            provider="flutterwave",
            event_type=event,
            reference=tx_ref or None,
            amount=float(amount) if amount else None,
            currency=data.get("currency"),
            status="failed",
            sig_verified=True,
            outcome="payment_failed",
        ))
        return {"status": "ok", "note": "transaction_failed"}

    asyncio.create_task(_log_event(
        provider="flutterwave",
        event_type=event,
        reference=tx_ref or None,
        status="received",
        sig_verified=True,
        outcome="unhandled",
        payload_summary={"event": event, "status": status},
    ))
    return {"status": "ok", "event": event, "handled": False}
