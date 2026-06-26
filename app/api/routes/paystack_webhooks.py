import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import PAYSTACK_SECRET_KEY
from app.db.database import get_db, AsyncSessionLocal
from app.db.models import User, UserSubscription, AuditLog
from app.api.routes.subscription import PLANS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/paystack", tags=["paystack-webhooks"])

def verify_paystack_signature(payload: bytes, signature: str) -> bool:
    if not PAYSTACK_SECRET_KEY:
        return False
    hash = hmac.new(PAYSTACK_SECRET_KEY.encode('utf-8'), payload, hashlib.sha512).hexdigest()
    return hmac.compare_digest(hash, signature)

@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(None)
):
    """
    Handle Paystack webhooks for subscription payments.
    """
    payload = await request.body()
    if not x_paystack_signature or not verify_paystack_signature(payload, x_paystack_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        data = json.loads(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = data.get("event")
    event_data = data.get("data", {})

    logger.info(f"Paystack Webhook received: {event}")

    if event == "charge.success":
        # Handle successful payment
        metadata = event_data.get("metadata", {})
        user_id = metadata.get("vit_user_id")
        plan_name = metadata.get("vit_plan")
        billing = metadata.get("vit_billing", "monthly")

        if not user_id or not plan_name:
            logger.warning("Paystack webhook missing metadata user_id or plan_name")
            return {"status": "ignored"}

        async with AsyncSessionLocal() as db:
            # Get user
            user = (await db.execute(select(User).where(User.id == int(user_id)))).scalar_one_or_none()
            if not user:
                logger.error(f"User {user_id} not found in Paystack webhook")
                return {"status": "error", "message": "user not found"}

            user.subscription_tier = plan_name
            if plan_name == "validator":
                user.role = "validator"

            await db.commit()
            logger.info(f"User {user_id} upgraded to {plan_name} via Paystack")

    return {"status": "ok"}
