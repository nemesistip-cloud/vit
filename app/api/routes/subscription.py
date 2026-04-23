# app/api/routes/subscription.py
# VIT Sports Intelligence — Subscription Plans & Feature Gating

import hashlib
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import UserSubscription, AuditLog
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscription", tags=["subscription"])

# ── Plan Definitions ─────────────────────────────────────────────────────────
PLANS = {
    "free": {
        "name": "free",
        "display_name": "Free",
        "price_monthly": 0.0,
        "price_yearly": 0.0,
        "price_vit": 0,
        "prediction_limit_daily": 10,
        "markets": ["1x2"],
        "api_calls_per_day": 0,
        "cache_ttl_minutes": 60,
        "features": {
            "predictions": True,
            "basic_history": True,
            "advanced_analytics": False,
            "ai_insights": False,
            "accumulator_builder": False,
            "model_breakdown": False,
            "telegram_alerts": False,
            "bankroll_tools": False,
            "csv_upload": False,
            "priority_support": False,
            "submit_predictions": False,
            "validator_rewards": False,
            "governance_voting": False,
            "over_under": False,
            "btts": False,
            "asian_handicap": False,
        },
        "description": "Basic 1X2 predictions — 10 per day",
        "limits": {
            "predictions_per_day": 10,
            "history_rows": 20,
            "api_calls_per_day": 0,
        }
    },
    "analyst": {
        "name": "analyst",
        "display_name": "Analyst",
        "price_monthly": 49.0,
        "price_yearly": 441.0,
        "price_vit": 500,
        "prediction_limit_daily": 100,
        "markets": ["1x2", "over_under"],
        "api_calls_per_day": 1000,
        "cache_ttl_minutes": 10,
        "features": {
            "predictions": True,
            "basic_history": True,
            "advanced_analytics": True,
            "ai_insights": True,
            "accumulator_builder": True,
            "model_breakdown": True,
            "telegram_alerts": True,
            "bankroll_tools": True,
            "csv_upload": True,
            "priority_support": False,
            "submit_predictions": False,
            "validator_rewards": False,
            "governance_voting": False,
            "over_under": True,
            "btts": False,
            "asian_handicap": False,
        },
        "description": "1X2 + Over/Under · 100 predictions/day · API access",
        "limits": {
            "predictions_per_day": 100,
            "history_rows": 500,
            "api_calls_per_day": 1000,
        }
    },
    "pro": {
        "name": "pro",
        "display_name": "Pro",
        "price_monthly": 99.0,
        "price_yearly": 891.0,
        "price_vit": 1000,
        "prediction_limit_daily": 500,
        "markets": ["1x2", "over_under", "btts", "asian_handicap", "correct_score"],
        "api_calls_per_day": 10000,
        "cache_ttl_minutes": 5,
        "features": {
            "predictions": True,
            "basic_history": True,
            "advanced_analytics": True,
            "ai_insights": True,
            "accumulator_builder": True,
            "model_breakdown": True,
            "telegram_alerts": True,
            "bankroll_tools": True,
            "csv_upload": True,
            "priority_support": True,
            "submit_predictions": False,
            "validator_rewards": False,
            "governance_voting": False,
            "over_under": True,
            "btts": True,
            "asian_handicap": True,
        },
        "description": "All 5 markets · 500 predictions/day · Priority support",
        "limits": {
            "predictions_per_day": 500,
            "history_rows": 2000,
            "api_calls_per_day": 10000,
        }
    },
    "validator": {
        "name": "validator",
        "display_name": "Validator",
        "price_monthly": 199.0,
        "price_yearly": 1791.0,
        "price_vit": 2000,
        "prediction_limit_daily": None,
        "markets": ["1x2", "over_under", "btts", "asian_handicap", "correct_score"],
        "api_calls_per_day": 100000,
        "cache_ttl_minutes": 1,
        "features": {
            "predictions": True,
            "basic_history": True,
            "advanced_analytics": True,
            "ai_insights": True,
            "accumulator_builder": True,
            "model_breakdown": True,
            "telegram_alerts": True,
            "bankroll_tools": True,
            "csv_upload": True,
            "priority_support": True,
            "submit_predictions": True,
            "validator_rewards": True,
            "governance_voting": True,
            "over_under": True,
            "btts": True,
            "asian_handicap": True,
        },
        "description": "Unlimited · Submit predictions · Earn from pool · Governance",
        "limits": {
            "predictions_per_day": None,
            "history_rows": None,
            "api_calls_per_day": 100000,
        }
    }
}


def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_plan(plan_name: str) -> dict:
    return PLANS.get(plan_name, PLANS["free"])


async def get_user_plan(api_key: str, db: AsyncSession) -> dict:
    """Return the full plan definition for a given API key."""
    if not api_key:
        return PLANS["free"]
    key_hash = _hash_api_key(api_key)
    result = await db.execute(
        select(UserSubscription).where(UserSubscription.api_key_hash == key_hash)
    )
    sub = result.scalar_one_or_none()
    if not sub or sub.status != "active":
        return PLANS["free"]
    return PLANS.get(sub.plan_name, PLANS["free"])


def _next_plan(current: str) -> str:
    """Return the next plan tier above current."""
    order = ["free", "analyst", "pro", "validator"]
    try:
        idx = order.index(current)
        return order[idx + 1] if idx + 1 < len(order) else "validator"
    except ValueError:
        return "analyst"


async def require_feature(feature: str, api_key: str, db: AsyncSession):
    """Raise 403 if the user's plan doesn't include a feature."""
    plan = await get_user_plan(api_key, db)
    if not plan["features"].get(feature, False):
        upgrade_to = _next_plan(plan["name"])
        upgrade_display = PLANS.get(upgrade_to, {}).get("display_name", upgrade_to.title())
        raise HTTPException(
            status_code=403,
            detail={
                "error": "feature_gated",
                "feature": feature,
                "current_plan": plan["name"],
                "upgrade_to": upgrade_to,
                "message": (
                    f"'{feature}' is not available on the {plan['display_name']} plan. "
                    f"Upgrade to {upgrade_display} to unlock."
                ),
            }
        )


# ── Schemas ────────────────────────────────────────────────────────────────
class UpgradePlanRequest(BaseModel):
    plan: str
    payment_token: Optional[str] = None  # Stripe token (future)


class AdminSetPlanRequest(BaseModel):
    api_key_target: str
    plan: str


# ── Routes ────────────────────────────────────────────────────────────────
@router.get("/plans")
async def list_plans():
    """Public: list all subscription plans."""
    return {"plans": list(PLANS.values())}


@router.get("/my-plan")
async def get_my_plan(request: Request, db: AsyncSession = Depends(get_db)):
    """Return current user's plan details."""
    api_key = request.headers.get("x-api-key", "")
    plan = await get_user_plan(api_key, db)

    key_hash = _hash_api_key(api_key) if api_key else None
    sub = None
    if key_hash:
        result = await db.execute(
            select(UserSubscription).where(UserSubscription.api_key_hash == key_hash)
        )
        sub = result.scalar_one_or_none()

    return {
        "plan": plan,
        "subscription": {
            "status": sub.status if sub else "none",
            "period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
            "stripe_customer_id": sub.stripe_customer_id if sub else None,
        } if sub else None,
        "usage": {
            "predictions_today": sub.prediction_count_today if sub else 0,
            "limit_today": plan["limits"]["predictions_per_day"],
        }
    }


class CheckoutRequest(BaseModel):
    plan: str
    billing: str = "monthly"  # monthly or yearly
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


@router.post("/create-checkout")
async def create_checkout_session(
    body: CheckoutRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe checkout session for subscription upgrade."""
    if body.plan not in PLANS or body.plan == "free":
        raise HTTPException(status_code=400, detail="Invalid plan for checkout")

    plan = PLANS[body.plan]
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Payment system not configured. Contact support.")
    if not (stripe_key.startswith("sk_test_") or stripe_key.startswith("sk_live_")):
        raise HTTPException(status_code=503, detail="Payment system configuration error. Contact support.")

    price_usd = plan["price_yearly"] if body.billing == "yearly" else plan["price_monthly"]
    amount_cents = int(price_usd * 100)
    period_label = "year" if body.billing == "yearly" else "month"

    domain = os.environ.get("REPLIT_DEV_DOMAIN") or os.environ.get("REPL_SLUG", "localhost")
    if "replit" not in domain and "localhost" not in domain:
        base_url = f"https://{domain}"
    else:
        base_url = f"https://{domain}"

    success_url = body.success_url or f"{base_url}/subscription?upgraded=true&plan={body.plan}"
    cancel_url = body.cancel_url or f"{base_url}/subscription?cancelled=true"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.stripe.com/v1/checkout/sessions",
                auth=(stripe_key, ""),
                data={
                    "payment_method_types[]": "card",
                    "line_items[0][price_data][currency]": "usd",
                    "line_items[0][price_data][product_data][name]": f"VIT {plan['display_name']} Plan",
                    "line_items[0][price_data][product_data][description]": f"{plan['description']} — billed per {period_label}",
                    "line_items[0][price_data][unit_amount]": str(amount_cents),
                    "line_items[0][quantity]": "1",
                    "mode": "payment",
                    "customer_email": current_user.email,
                    "client_reference_id": str(current_user.id),
                    "success_url": success_url,
                    "cancel_url": cancel_url,
                    "metadata[vit_plan]": body.plan,
                    "metadata[vit_user_id]": str(current_user.id),
                    "metadata[vit_billing]": body.billing,
                },
            )

        if resp.status_code != 200:
            err = resp.json().get("error", {})
            logger.error(f"Stripe checkout error: {err}")
            user_msg = err.get("message", "Payment processing error")
            if "sk_" in user_msg or "mk_" in user_msg or "rk_" in user_msg:
                user_msg = "Invalid payment configuration. Please contact support."
            raise HTTPException(status_code=502, detail=user_msg)

        session = resp.json()
        return {
            "checkout_url": session["url"],
            "session_id": session["id"],
            "plan": body.plan,
            "amount_usd": price_usd,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stripe checkout exception: {e}")
        raise HTTPException(status_code=502, detail="Failed to create checkout session. Please try again.")


@router.post("/upgrade")
async def upgrade_plan(
    body: UpgradePlanRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Upgrade plan directly (used by admins or post-payment webhook confirmation).
    For user-initiated upgrades, use /subscription/create-checkout instead.
    """
    api_key = request.headers.get("x-api-key", "")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required to manage subscription")

    if body.plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {body.plan}")

    key_hash = _hash_api_key(api_key)

    result = await db.execute(
        select(UserSubscription).where(UserSubscription.api_key_hash == key_hash)
    )
    sub = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if sub:
        sub.plan_name = body.plan
        sub.status = "active"
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(days=30)
    else:
        sub = UserSubscription(
            api_key_hash=key_hash,
            plan_name=body.plan,
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db.add(sub)

    audit = AuditLog(
        action="subscription_upgrade",
        actor=key_hash[:8] + "...",
        resource="subscription",
        details={"plan": body.plan, "source": "direct"},
        ip_address=request.client.host if request.client else None,
        status="success",
    )
    db.add(audit)
    await db.commit()

    return {
        "success": True,
        "plan": PLANS[body.plan],
        "message": f"Successfully upgraded to {PLANS[body.plan]['display_name']} plan.",
    }


@router.post("/admin/set-plan")
async def admin_set_plan(
    body: AdminSetPlanRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint: manually set a plan for any API key."""
    admin_key = os.getenv("API_KEY", "")
    req_key = request.headers.get("x-api-key", "")
    if admin_key and req_key != admin_key:
        raise HTTPException(status_code=403, detail="Admin access required")

    if body.plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {body.plan}")

    key_hash = _hash_api_key(body.api_key_target)
    result = await db.execute(
        select(UserSubscription).where(UserSubscription.api_key_hash == key_hash)
    )
    sub = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if sub:
        sub.plan_name = body.plan
        sub.status = "active"
        sub.current_period_end = now + timedelta(days=365)
    else:
        sub = UserSubscription(
            api_key_hash=key_hash,
            plan_name=body.plan,
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=365),
        )
        db.add(sub)

    audit = AuditLog(
        action="admin_set_plan",
        actor="admin",
        resource="subscription",
        details={"target_key_hash": key_hash[:8] + "...", "plan": body.plan},
        ip_address=request.client.host if request.client else None,
        status="success",
    )
    db.add(audit)
    await db.commit()
    return {"success": True, "plan": body.plan}
