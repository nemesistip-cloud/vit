import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import PAYSTACK_SECRET_KEY, PAYSTACK_WEBHOOK_SECRET
from app.db.database import get_db, AsyncSessionLocal
from app.db.models import User, UserSubscription, AuditLog
from app.api.routes.subscription import PLANS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/paystack", tags=["paystack-webhooks"])


def verify_paystack_signature(payload: bytes, signature: str) -> bool:
    """Validate the X-Paystack-Signature header.

    Prefers PAYSTACK_WEBHOOK_SECRET (a dedicated webhook validation secret)
    over PAYSTACK_SECRET_KEY so the two concerns — making API calls TO Paystack
    and validating inbound webhook payloads — use separate secrets.

    Per Paystack docs the signature is HMAC-SHA512 of the raw request body
    using the secret key.  If neither secret is configured the request is
    rejected (returns False) so unsigned payloads are never silently accepted.
    """
    # Prefer dedicated webhook secret; fall back to the API secret key.
    signing_secret = PAYSTACK_WEBHOOK_SECRET or PAYSTACK_SECRET_KEY
    if not signing_secret:
        logger.error(
            "verify_paystack_signature: neither PAYSTACK_WEBHOOK_SECRET nor "
            "PAYSTACK_SECRET_KEY is configured — rejecting webhook."
        )
        return False

    expected = hmac.new(
        signing_secret.encode("utf-8"), payload, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


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
