# app/api/routes/stripe_webhooks.py
# Stripe Webhook Handler — Process subscription payment events

import os
import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib
import hmac

from app.db.database import get_db
from app.db.models import UserSubscription, AuditLog, User
from app.api.routes.subscription import PLANS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])


def _verify_stripe_signature(payload: bytes, sig_header: str, webhook_secret: str) -> bool:
    """Verify Stripe webhook signature."""
    try:
        timestamp, signature = sig_header.split(",")
        timestamp = timestamp.split("=")[1]
        signature = signature.split("=")[1]
        
        signed_content = f"{timestamp}.{payload.decode()}"
        expected_sig = hmac.new(
            webhook_secret.encode(),
            signed_content.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_sig)
    except Exception as e:
        logger.error(f"Stripe signature verification failed: {e}")
        return False


@router.post("/stripe/checkout")
async def handle_stripe_checkout_complete(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Stripe checkout.session.completed event.
    Activates subscription and creates user API key.
    """
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    
    if not _verify_stripe_signature(payload, sig_header, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    if event["type"] != "checkout.session.completed":
        return {"received": True}
    
    session = event["data"]["object"]
    client_ref_id = session.get("client_reference_id")  # user ID
    vit_plan = session.get("metadata", {}).get("vit_plan")
    vit_billing = session.get("metadata", {}).get("vit_billing", "monthly")
    
    if not client_ref_id or not vit_plan or vit_plan not in PLANS:
        logger.warning(f"Invalid checkout session metadata: {session}")
        return {"received": True}
    
    try:
        user_id = int(client_ref_id)
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User not found for checkout: {user_id}")
            return {"received": True}
        
        # Create or update subscription
        key_hash = hashlib.sha256(f"{user.id}:stripe:{session['id']}".encode()).hexdigest()
        
        result = await db.execute(
            select(UserSubscription).where(UserSubscription.api_key_hash == key_hash)
        )
        sub = result.scalar_one_or_none()
        
        now = datetime.now(timezone.utc)
        period_days = 365 if vit_billing == "yearly" else 30;
        
        if sub:
            sub.plan_name = vit_plan
            sub.status = "active"
            sub.current_period_start = now
            sub.current_period_end = now + timedelta(days=period_days)
            sub.stripe_customer_id = session.get("customer")
            sub.stripe_session_id = session["id"]
        else:
            import uuid
            api_key = str(uuid.uuid4())
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            sub = UserSubscription(
                user_id=user_id,
                api_key=api_key,
                api_key_hash=api_key_hash,
                plan_name=vit_plan,
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=period_days),
                stripe_customer_id=session.get("customer"),
                stripe_session_id=session["id"],
            )
            db.add(sub)
        
        audit = AuditLog(
            action="subscription_payment_received",
            actor=f"stripe:{session['id']}",
            resource="subscription",
            details={
                "plan": vit_plan,
                "billing": vit_billing,
                "amount": session.get("amount_total", 0) / 100,
                "currency": session.get("currency", "usd"),
            },
            status="success",
        )
        db.add(audit)
        await db.commit()
        
        logger.info(f"Subscription activated: user={user_id} plan={vit_plan}")
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return {"received": True, "error": str(e)}
    
    return {"received": True}


@router.post("/stripe/invoice-paid")
async def handle_stripe_invoice_paid(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Stripe invoice.payment_succeeded event.
    Extends subscription period for recurring payments.
    """
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    
    if not _verify_stripe_signature(payload, sig_header, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    if event["type"] != "invoice.payment_succeeded":
        return {"received": True}
    
    invoice = event["data"]["object"]
    customer_id = invoice.get("customer")
    
    if not customer_id:
        logger.warning("invoice.payment_succeeded: no customer_id")
        return {"received": True}
    
    try:
        result = await db.execute(
            select(UserSubscription).where(
                UserSubscription.stripe_customer_id == customer_id,
                UserSubscription.status == "active",
            )
        )
        sub = result.scalar_one_or_none()
        
        if not sub:
            logger.warning(f"No subscription found for customer: {customer_id}")
            return {"received": True}
        
        # Determine billing period from subscription interval
        # For now, assume monthly (30 days)
        period_days = 30
        sub.current_period_end = sub.current_period_end + timedelta(days=period_days)
        
        audit = AuditLog(
            action="subscription_invoice_paid",
            actor=f"stripe:invoice:{invoice['id']}",
            resource="subscription",
            details={
                "plan": sub.plan_name,
                "amount": invoice.get("amount_paid", 0) / 100,
                "currency": invoice.get("currency", "usd"),
            },
            status="success",
        )
        db.add(audit)
        await db.commit()
        
        logger.info(f"Subscription renewed: customer={customer_id} until={sub.current_period_end}")
        
    except Exception as e:
        logger.error(f"Invoice webhook error: {e}")
        return {"received": True, "error": str(e)}
    
    return {"received": True}


@router.post("/stripe/customer-subscription-deleted")
async def handle_stripe_subscription_deleted(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Stripe customer.subscription.deleted event.
    Marks subscription as cancelled.
    """
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    
    if not _verify_stripe_signature(payload, sig_header, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    if event["type"] != "customer.subscription.deleted":
        return {"received": True}
    
    subscription = event["data"]["object"]
    customer_id = subscription.get("customer")
    
    if not customer_id:
        return {"received": True}
    
    try:
        result = await db.execute(
            select(UserSubscription).where(
                UserSubscription.stripe_customer_id == customer_id
            )
        )
        sub = result.scalar_one_or_none()
        
        if sub:
            sub.status = "cancelled"
            sub.current_period_end = datetime.now(timezone.utc)
            
            audit = AuditLog(
                action="subscription_cancelled",
                actor=f"stripe:subscription:{subscription['id']}",
                resource="subscription",
                details={"reason": "customer_action"},
                status="success",
            )
            db.add(audit)
            await db.commit()
            
            logger.info(f"Subscription cancelled: customer={customer_id}")
    
    except Exception as e:
        logger.error(f"Subscription delete webhook error: {e}")
    
    return {"received": True}