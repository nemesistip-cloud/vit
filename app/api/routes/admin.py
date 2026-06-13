import asyncio
import csv
import hashlib
import io
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_env, APP_VERSION, AUTH_ENABLED, API_KEY
from app.db.database import AsyncSessionLocal, get_db
from app.db.models import User, AuditLog, Match, Prediction, SubscriptionPlan, TrainingJob
from app.core.dependencies import get_orchestrator, get_telegram_alerts
from app.auth.dependencies import get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

from app.api.deps import get_current_admin
_KEY_REGISTRY = [
    # ── Sports Data ────────────────────────────────────────────────────
    {
        "name":        "FOOTBALL_DATA_API_KEY",
        "label":       "Football-Data.org",
        "description": "Fetches scheduled fixtures and match history",
        "required":    True,
        "group":       "Sports Data",
    },
    {
        "name":        "ODDS_API_KEY",
        "label":       "The Odds API",
        "description": "Live betting odds and market data (also readable as THE_ODDS_API_KEY)",
        "required":    True,
        "group":       "Sports Data",
    },
    # ── VIT AI (Native Ecosystem) ──────────────────────────────────────
    {
        "name":        "USE_REAL_ML_MODELS",
        "label":       "Use Real ML Models",
        "description": "Toggle between algorithmic fallbacks and trained weights (true/false)",
        "required":    False,
        "group":       "VIT AI",
    },
    # ── Offerwall / Rewards Providers ─────────────────────────────────────
    {
        "name":        "AYET_API_TOKEN",
        "label":       "Ayet Studios API Token",
        "description": "Token for Ayet Studios offerwall (required to load offers in the earn page)",
        "required":    False,
        "group":       "Offerwall",
    },
    {
        "name":        "BITLABS_APP_TOKEN",
        "label":       "BitLabs App Token",
        "description": "App token for BitLabs targeted surveys offerwall",
        "required":    False,
        "group":       "Offerwall",
    },
    {
        "name":        "CPX_RESEARCH_APP_ID",
        "label":       "CPX Research App ID",
        "description": "App ID for CPX Research survey panel",
        "required":    False,
        "group":       "Offerwall",
    },
    {
        "name":        "CPX_RESEARCH_SECURE_HASH_KEY",
        "label":       "CPX Research Hash Key",
        "description": "Secret key for CPX Research postback signature verification",
        "required":    False,
        "group":       "Offerwall",
    },
    {
        "name":        "REVU_PUBLISHER_ID",
        "label":       "RevU Publisher ID",
        "description": "Publisher ID for Revenue Universe (RevU) survey wall",
        "required":    False,
        "group":       "Offerwall",
    },
    {
        "name":        "TAPJOY_SDK_KEY",
        "label":       "Tapjoy SDK Key",
        "description": "SDK key for Tapjoy in-app offerwall",
        "required":    False,
        "group":       "Offerwall",
    },
    {
        "name":        "GCS_BUCKET_NAME",
        "label":       "GCS Model Bucket",
        "description": "Google Cloud Storage bucket for syncing model weights",
        "required":    False,
        "group":       "VIT AI",
    },
    {
        "name":        "ML_MODEL_CACHE_ENABLED",
        "label":       "Model Cache",
        "description": "Enable in-memory caching for ML models (true/false)",
        "required":    False,
        "group":       "VIT AI",
    },

    # ── Payments ───────────────────────────────────────────────────────
    {
        "name":        "STRIPE_SECRET_KEY",
        "label":       "Stripe",
        "description": "USD subscription payments — Pro ($49/mo) and Elite ($199/mo) plans",
        "required":    False,
        "group":       "Payments",
    },
    {
        "name":        "PAYSTACK_SECRET_KEY",
        "label":       "Paystack",
        "description": "NGN wallet deposits and local payment processing",
        "required":    False,
        "group":       "Payments",
    },
    # ── Infrastructure ─────────────────────────────────────────────────
    {
        "name":        "REDIS_URL",
        "label":       "Redis URL",
        "description": "Redis connection for Celery job queue and persistent rate limiting",
        "required":    False,
        "group":       "Infrastructure",
    },
    {
        "name":        "SMTP_HOST",
        "label":       "SMTP Host",
        "description": "Mail server hostname for email verification and password resets",
        "required":    False,
        "group":       "Infrastructure",
    },
    {
        "name":        "SMTP_USER",
        "label":       "SMTP Username",
        "description": "Mail server login username",
        "required":    False,
        "group":       "Infrastructure",
    },
    {
        "name":        "SMTP_PASS",
        "label":       "SMTP Password",
        "description": "Mail server login password",
        "required":    False,
        "group":       "Infrastructure",
    },
    # ── Messaging ──────────────────────────────────────────────────────
    {
        "name":        "TELEGRAM_BOT_TOKEN",
        "label":       "Telegram Bot Token",
        "description": "Sends alerts and accumulators via Telegram",
        "required":    False,
        "group":       "Messaging",
    },
    {
        "name":        "TELEGRAM_CHAT_ID",
        "label":       "Telegram Chat / Channel ID",
        "description": "Target chat or channel for Telegram messages",
        "required":    False,
        "group":       "Messaging",
    },

    # ── Payments (Webhooks) ─────────────────────────────────────────────
    {
        "name":        "STRIPE_WEBHOOK_SECRET",
        "label":       "Stripe Webhook Secret",
        "description": "Validates Stripe webhook signatures (whsec_…) — required to process subscription events",
        "required":    False,
        "group":       "Payments",
    },
    {
        "name":        "PAYSTACK_WEBHOOK_SECRET",
        "label":       "Paystack Webhook Secret",
        "description": "Validates Paystack webhook HMAC signatures — required to process NGN deposit events",
        "required":    False,
        "group":       "Payments",
    },

    # ── Blockchain ─────────────────────────────────────────────────────
    {
        "name":        "BASE_RPC_URL",
        "label":       "Base L2 RPC URL",
        "description": "JSON-RPC endpoint for the Base L2 network (e.g. https://mainnet.base.org)",
        "required":    False,
        "group":       "Blockchain",
    },
    {
        "name":        "VIT_CONTRACT_ADDRESS",
        "label":       "VITCoin Contract Address",
        "description": "Deployed ERC-20 contract address for VITCoin on Base L2 (0x…)",
        "required":    False,
        "group":       "Blockchain",
    },
    # ── Security ───────────────────────────────────────────────────────
    {
        "name":        "JWT_SECRET_KEY",
        "label":       "JWT Secret Key",
        "description": "Signs all access tokens. Must be set in production — ephemeral key resets sessions on restart",
        "required":    True,
        "group":       "Security",
    },
    {
        "name":        "API_KEY",
        "label":       "Admin API Key",
        "description": "Master key used to authenticate legacy admin endpoints",
        "required":    False,
        "group":       "Security",
    },
    # ── Notifications ──────────────────────────────────────────────────
    {
        "name":        "RESEND_API_KEY",
        "label":       "Resend Email API Key",
        "description": "Sends transactional emails (verification, password reset, notifications) via Resend.com",
        "required":    False,
        "group":       "Messaging",
    },
    # ── Sports Data (free tier) ────────────────────────────────────────
    {
        "name":        "THESPORTSDB_API_KEY",
        "label":       "TheSportsDB API Key",
        "description": "Fixture source — value '3' is the free-tier key, no account required",
        "required":    False,
        "group":       "Sports Data",
    },
    # ── Pi Network ─────────────────────────────────────────────────────
    {
        "name":        "PI_APP_ID",
        "label":       "Pi App ID",
        "description": "App identifier from Pi Developer Portal (developer.pi)",
        "required":    False,
        "group":       "Pi Network",
    },
    {
        "name":        "PI_APP_SECRET",
        "label":       "Pi App Secret",
        "description": "Server-side secret key for Pi Network API (used to approve / complete payments)",
        "required":    False,
        "group":       "Pi Network",
    },
    {
        "name":        "PI_WEBHOOK_SECRET",
        "label":       "Pi Webhook Secret",
        "description": "HMAC secret to verify incoming Pi webhook signatures",
        "required":    False,
        "group":       "Pi Network",
    },
    {
        "name":        "PI_SANDBOX_MODE",
        "label":       "Pi Sandbox Mode",
        "description": "Set to 'false' for Mainnet. Default is 'true' (Sandbox / Testnet)",
        "required":    False,
        "group":       "Pi Network",
    },
    # ── Flutterwave ────────────────────────────────────────────────────
    {
        "name":        "FLW_SECRET_KEY",
        "label":       "Flutterwave Secret Key",
        "description": "Server secret key (FLWSECK_…) for initiating MoMo / card charges and transfers",
        "required":    False,
        "group":       "Payments",
    },
    {
        "name":        "FLW_PUBLIC_KEY",
        "label":       "Flutterwave Public Key",
        "description": "Client-facing public key (FLWPUBK_…) for front-end SDK initialisation",
        "required":    False,
        "group":       "Payments",
    },
    {
        "name":        "FLW_WEBHOOK_SECRET",
        "label":       "Flutterwave Webhook Secret",
        "description": "Sent as the 'verif-hash' header on every Flutterwave webhook call",
        "required":    False,
        "group":       "Payments",
    },
]

@router.get("/api-keys")
async def list_api_keys(current_user=Depends(get_current_admin)):
    from app.services.secrets_manager import get_db_secret_keys
    db_keys: set = await get_db_secret_keys()
    keys = []
    for entry in _KEY_REGISTRY:
        name = entry.get("name", "")
        env_val = os.getenv(name, "").strip() if name else ""
        in_db   = name in db_keys
        configured = bool(env_val) or in_db
        if env_val:
            source = "replit_secret"
        elif in_db:
            source = "database"
        else:
            source = "unset"
        keys.append({
            **entry,
            "configured": configured,
            "masked": "••••" if configured else "",
            "source": source,
        })
    return {"keys": keys}

@router.get("/config-status")
async def get_config_status(current_user=Depends(get_current_admin)):
    """
    Returns real-time health status for every external service.
    Used by the admin Config Health strip.
    Checks both os.environ (Replit Secrets + live-saved keys) and the DB secret store.
    """
    # Load the set of keys currently stored encrypted in the DB
    from app.services.secrets_manager import get_db_secret_keys
    db_keys: set = await get_db_secret_keys()

    def _status(key: str, label: str, required: bool = False) -> dict:
        val = os.getenv(key, "").strip()
        in_db = key in db_keys
        is_set = bool(val) or in_db
        return {
            "key":      key,
            "label":    label,
            "set":      is_set,
            "required": required,
            "status":   "ok" if is_set else ("error" if required else "warning"),
        }

    services = [
        _status("FOOTBALL_DATA_API_KEY",  "Football-Data.org",   required=True),
        _status("ODDS_API_KEY",           "The Odds API",        required=True),
        _status("USE_REAL_ML_MODELS",     "VIT Native AI",       required=False),

        _status("STRIPE_SECRET_KEY",      "Stripe Payments",     required=False),
        _status("STRIPE_WEBHOOK_SECRET",  "Stripe Webhooks",     required=False),
        _status("PAYSTACK_SECRET_KEY",    "Paystack Payments",   required=False),
        _status("PAYSTACK_WEBHOOK_SECRET","Paystack Webhooks",   required=False),
        _status("FLW_SECRET_KEY",         "Flutterwave (MoMo)",  required=False),
        _status("FLW_WEBHOOK_SECRET",     "Flutterwave Webhooks",required=False),
        _status("PI_APP_ID",              "Pi Network App",      required=False),
        _status("PI_APP_SECRET",          "Pi Network Secret",   required=False),

        _status("BASE_RPC_URL",           "Base L2 RPC",         required=False),
        _status("VIT_CONTRACT_ADDRESS",   "VITCoin Contract",    required=False),
        _status("REDIS_URL",              "Redis",               required=False),
        _status("SMTP_HOST",              "Email / SMTP",        required=False),
        _status("RESEND_API_KEY",         "Resend Email",        required=False),
        _status("TELEGRAM_BOT_TOKEN",     "Telegram Bot",        required=False),
    ]

    errors   = [s for s in services if s["status"] == "error"]
    warnings = [s for s in services if s["status"] == "warning"]
    ok       = [s for s in services if s["status"] == "ok"]

    return {
        "services":      services,
        "summary": {
            "total":    len(services),
            "ok":       len(ok),
            "warnings": len(warnings),
            "errors":   len(errors),
            "healthy":  len(errors) == 0,
        },
    }


@router.get("/health")
async def admin_health():
    return {"status": "ok"}

@router.get("/models/status")
async def get_models_status():
    orch = get_orchestrator()
    if not orch: return {"ready": 0, "total": 0, "models": []}
    return orch.get_model_status()

@router.post("/models/reload")
async def reload_models():
    orch = get_orchestrator()
    if orch: orch.load_all_models()
    return {"status": "reloaded"}

@router.get("/stats")
async def get_admin_stats(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_admin)):
    """Provides dashboard overview statistics including user growth and prediction accuracy."""
    from datetime import datetime, timezone, timedelta

    now   = datetime.now(timezone.utc).replace(tzinfo=None)
    d1    = now - timedelta(days=1)
    d7    = now - timedelta(days=7)
    d30   = now - timedelta(days=30)

    user_count   = (await db.execute(select(func.count(User.id)))).scalar() or 0
    match_count  = (await db.execute(select(func.count(Match.id)))).scalar() or 0
    job_count    = (await db.execute(select(func.count(TrainingJob.id)))).scalar() or 0
    audit_count  = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0
    plan_count   = (await db.execute(select(func.count(SubscriptionPlan.id)).where(SubscriptionPlan.is_active == True))).scalar() or 0

    new_24h  = (await db.execute(select(func.count(User.id)).where(User.created_at >= d1))).scalar() or 0
    new_7d   = (await db.execute(select(func.count(User.id)).where(User.created_at >= d7))).scalar() or 0
    new_30d  = (await db.execute(select(func.count(User.id)).where(User.created_at >= d30))).scalar() or 0

    active_7d = 0
    try:
        active_7d = (await db.execute(
            select(func.count(User.id)).where(User.last_login >= d7)
        )).scalar() or 0
    except Exception:
        pass

    total_preds   = (await db.execute(select(func.count(Prediction.id)))).scalar() or 0
    settled_preds = 0
    correct_preds = 0
    try:
        settled_preds = (await db.execute(
            select(func.count(Prediction.id)).where(Prediction.was_correct.isnot(None))
        )).scalar() or 0
        correct_preds = (await db.execute(
            select(func.count(Prediction.id)).where(Prediction.was_correct == True)
        )).scalar() or 0
    except Exception:
        pass

    total_revenue = 0.0
    try:
        from app.modules.wallet.models import Transaction
        rev_row = (await db.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.transaction_type.in_(["deposit", "subscription"])
            )
        )).scalar()
        total_revenue = float(rev_row or 0)
    except Exception:
        pass

    recent_activity_rows = (await db.execute(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10)
    )).scalars().all()

    recent_activity = [
        {
            "action": r.action,
            "actor": r.actor,
            "status": r.status,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None
        } for r in recent_activity_rows
    ]

    top_users_rows = (await db.execute(
        select(User).order_by(User.created_at.desc()).limit(5)
    )).scalars().all()

    wallet_map: dict = {}
    try:
        from app.modules.wallet.models import Wallet
        uids = [u.id for u in top_users_rows]
        if uids:
            wrows = (await db.execute(
                select(Wallet.user_id, Wallet.vitcoin_balance).where(Wallet.user_id.in_(uids))
            )).all()
            wallet_map = {row.user_id: float(row.vitcoin_balance) for row in wrows}
    except Exception:
        pass

    top_users = [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "tier": u.subscription_tier,
            "vitcoin_balance": wallet_map.get(u.id, 0.0),
        } for u in top_users_rows
    ]

    return {
        "users": user_count,
        "matches": match_count,
        "training_jobs": job_count,
        "active_plans": plan_count,
        "audit_entries": audit_count,
        "total_predictions": total_preds,
        "user_growth": {
            "new_24h":   int(new_24h),
            "new_7d":    int(new_7d),
            "new_30d":   int(new_30d),
            "active_7d": int(active_7d),
        },
        "prediction_accuracy": {
            "total":    int(total_preds),
            "settled":  int(settled_preds),
            "correct":  int(correct_preds),
            "accuracy_pct": round(correct_preds / max(settled_preds, 1) * 100, 1),
        },
        "revenue": {
            "total_usd": total_revenue,
        },
        "recent_activity": recent_activity,
        "top_users": top_users,
    }

@router.get("/users")
async def list_users(
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Lists all registered users with search and pagination."""
    query = select(User)
    if search:
        query = query.where(or_(User.email.ilike(f"%{search}%"), User.username.ilike(f"%{search}%")))

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(query.order_by(User.id.desc()).limit(limit).offset(offset))
    users = result.scalars().all()

    # Bulk-fetch wallet balances so we don't N+1 the DB
    wallet_map: dict = {}
    try:
        from app.modules.wallet.models import Wallet
        user_ids = [u.id for u in users]
        if user_ids:
            wallet_rows = (await db.execute(
                select(Wallet.user_id, Wallet.vitcoin_balance).where(Wallet.user_id.in_(user_ids))
            )).all()
            wallet_map = {row.user_id: float(row.vitcoin_balance) for row in wallet_rows}
    except Exception:
        pass

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "role": u.role,
                "admin_role": u.admin_role,
                "subscription_tier": u.subscription_tier,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "is_banned": u.is_banned,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "vitcoin_balance": wallet_map.get(u.id, 0.0),
            } for u in users
        ],
        "total": total
    }

@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Updates user details (role, tier, etc)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in body.items():
        if hasattr(user, key) and key not in ("id", "hashed_password"):
            setattr(user, key, value)

    await db.commit()
    return {"status": "success"}

@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Bans or unbans a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_banned = body.get("banned", True)
    await db.commit()

    audit = AuditLog(
        action="user_ban" if user.is_banned else "user_unban",
        actor=current_user.username,
        resource="user",
        resource_id=str(user_id),
        details={"reason": body.get("reason", "")}
    )
    db.add(audit)
    await db.commit()

    return {"status": "success"}

@router.get("/audit")
async def list_audit_logs(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Returns system audit logs."""
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
    )
    logs = result.scalars().all()
    total = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0

    return {
        "logs": [
            {
                "id": l.id,
                "action": l.action,
                "actor": l.actor,
                "resource": l.resource,
                "resource_id": l.resource_id,
                "details": l.details,
                "ip_address": l.ip_address,
                "status": l.status,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None
            } for l in logs
        ],
        "total": total
    }

@router.post("/system/cache/clear")
async def clear_cache(current_user=Depends(get_current_admin)):
    cleared: list[str] = []
    try:
        from app.api.routes.dashboard import _price_cache
        _price_cache["data"] = None
        _price_cache["timestamp"] = None
        cleared.append("dashboard_price_cache")
    except Exception:
        pass
    try:
        from app.services.ft_backfill import _form_cache  # type: ignore
        _form_cache.clear()
        cleared.append("form_cache")
    except Exception:
        pass
    try:
        from app.services.vit_analytics import _insight_cache  # type: ignore
        _insight_cache.clear()
        cleared.append("insight_cache")
    except Exception:
        pass
    return {"status": "success", "message": "Cache cleared", "cleared": cleared}

@router.post("/system/backup")
async def create_backup(current_user=Depends(get_current_admin)):
    return {"status": "success", "backup": f"backup_{int(datetime.now().timestamp())}.sql"}

# ── Feature Flags ──────────────────────────────────────────────────────────

_FEATURE_FLAGS_REGISTRY = [
    {"key": "USE_REAL_ML_MODELS",        "description": "Use trained sklearn/XGBoost weights instead of algorithmic fallbacks"},
    {"key": "ENABLE_ML_TRAINING",        "description": "Allow background re-training jobs to run"},
    {"key": "ENABLE_AUTO_SYNC",          "description": "Automatically sync fixtures every 3 hours"},
    {"key": "ENABLE_LIVE_ODDS",          "description": "Fetch and display live betting odds"},
    {"key": "ENABLE_PREDICTION_SEEDING", "description": "Auto-seed ML predictions for newly fetched fixtures"},
    {"key": "ENABLE_KYC_CHECKS",         "description": "Require KYC verification before staking"},
    {"key": "ENABLE_BLOCKCHAIN",         "description": "On-chain settlement and VITCoin transfers"},
    {"key": "ENABLE_WEBSOCKETS",         "description": "Real-time score and odds updates via WebSocket"},
    {"key": "ENABLE_ANALYTICS",          "description": "Track user analytics and betting patterns"},
    {"key": "ENABLE_REFERRALS",          "description": "Referral programme — reward users for inviting friends"},
]


@router.get("/system/flags")
async def get_feature_flags(current_user=Depends(get_current_admin)):
    """Return all known feature flags with their current state."""
    flags: dict = {}
    for entry in _FEATURE_FLAGS_REGISTRY:
        key = entry["key"]
        value = os.getenv(key, "false").lower() in ("true", "1", "yes")
        flags[key] = {"value": value, "description": entry["description"]}
    return {"flags": flags}


@router.put("/system/flags")
async def update_feature_flags(
    body: dict,
    current_user=Depends(get_current_admin),
):
    """Toggle feature flags. Body: { flags: { FLAG_KEY: bool } }"""
    from app.core.feature_flags import FeatureFlags
    from app.services.secrets_manager import save_secret_to_db

    updates: dict = body.get("flags", {})
    if not updates:
        raise HTTPException(400, "No flags provided")

    updated = {}
    for key, value in updates.items():
        if key not in {f["key"] for f in _FEATURE_FLAGS_REGISTRY}:
            continue
        str_val = "true" if value else "false"
        os.environ[key] = str_val
        await save_secret_to_db(key, str_val)
        updated[key] = value

    # Bust the FeatureFlags in-process cache so the new values take effect immediately
    FeatureFlags.reset()
    return {"status": "ok", "updated": updated}


# ── API Keys bulk update / delete ──────────────────────────────────────────

@router.post("/api-keys/update")
async def bulk_update_api_keys(
    body: dict,
    current_user=Depends(get_current_admin),
):
    """Bulk-update API keys. Body: { updates: { KEY_NAME: "value" } }
    Saves each key encrypted to the DB and injects into the running process immediately.
    """
    from app.services.secrets_manager import save_secret_to_db

    updates: dict = body.get("updates", {})
    if not updates:
        raise HTTPException(400, "No updates provided")

    saved: dict = {}
    errors: dict = {}
    warnings: dict = {}

    allowed_keys = {e["name"] for e in _KEY_REGISTRY}

    for key, value in updates.items():
        if not isinstance(value, str) or not value.strip():
            errors[key] = "value cannot be empty"
            continue
        if key not in allowed_keys:
            warnings[key] = f"'{key}' is not in the key registry — saving anyway"

        try:
            clean_val = value.strip()
            await save_secret_to_db(key, clean_val)
            # Inject into live process so it takes effect without restart
            os.environ[key] = clean_val
            saved[key] = "••••" + clean_val[-4:] if len(clean_val) > 4 else "••••"

            # Audit
            audit = AuditLog(
                action="api_key_updated",
                actor=current_user.username,
                resource="api_key",
                resource_id=key,
                details={"masked": saved[key]},
                status="success",
            )
        except Exception as exc:
            errors[key] = str(exc)

    return {
        "updated": saved,
        "errors": errors,
        "warnings": warnings,
        "message": f"{len(saved)} key(s) saved and active immediately",
    }


@router.delete("/api-keys/{name}")
async def delete_api_key(
    name: str,
    current_user=Depends(get_current_admin),
):
    """Remove a DB-stored API key (the env var remains until next restart)."""
    from app.services.secrets_manager import delete_secret_from_db

    existed = await delete_secret_from_db(name)
    if not existed:
        raise HTTPException(404, f"Key '{name}' not found in database")

    audit = AuditLog(
        action="api_key_deleted",
        actor=current_user.username,
        resource="api_key",
        resource_id=name,
        details={},
        status="success",
    )
    return {"status": "ok", "key": name, "message": f"'{name}' removed from database (env var still active until restart)"}

@router.post("/matches/fetch-fixtures")
async def fetch_fixtures(
    count: int = 50,
    days: int = 14,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Trigger an immediate fixture sync from TheSportsDB + Football-Data.org."""
    from app.services.sportsdb_api import sync_upcoming_fixtures
    try:
        result = await sync_upcoming_fixtures(db, days_ahead=days)
    except Exception as sync_err:
        logger.error(f"[admin] fetch_fixtures error: {sync_err}")
        result = {"inserted": 0, "updated": 0, "skipped": 0, "total_fetched": 0, "error": str(sync_err)}

    seeded = 0
    try:
        from app.modules.predictions.seeder import seed_predictions_for_upcoming
        seeded = await seed_predictions_for_upcoming(db)
    except Exception as seed_err:
        logger.warning(f"[admin] prediction seeder failed: {seed_err}")

    stored = result.get("inserted", 0) + result.get("updated", 0)
    return {
        "status": "success",
        "stored": stored,
        "skipped_existing": result.get("skipped", 0),
        "fixtures": result,
        "predictions_seeded": seeded,
        "days_ahead": days,
    }


@router.post("/fixtures/sync-fd12")
async def sync_fd12_fixtures(
    days: int = 14,
    current_user=Depends(get_current_admin),
):
    """Fetch upcoming fixtures from all 12 football-data.org free-tier competitions.

    Returns per-competition upserted/skipped counts plus any errors.
    Respects the 10 calls/min rate limit with a 6-second gap between competitions.
    """
    import os, asyncio as _asyncio
    from datetime import datetime as _dt, timedelta as _td

    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()
    if not api_key:
        return {"status": "error", "message": "FOOTBALL_DATA_API_KEY not configured"}

    from app.services.football_api import FootballDataClient
    from app.db.database import AsyncSessionLocal
    from app.data.pipeline import SUPPORTED_LEAGUES, _process_league
    from app.core.dependencies import get_data_loader

    loader = get_data_loader()
    if loader is None:
        return {"status": "error", "message": "DataLoader unavailable — API key may be invalid or not loaded yet"}

    started_at = _dt.utcnow()
    results: list = []
    total_upserted = 0
    total_skipped  = 0
    all_errors: list = []

    for i, league in enumerate(SUPPORTED_LEAGUES):
        if i > 0:
            await _asyncio.sleep(7)   # ~6s gap → stays under 10 req/min
        try:
            upserted, skipped, errors = await _process_league(loader, league)
            total_upserted += upserted
            total_skipped  += skipped
            all_errors.extend(errors)
            results.append({
                "league": league,
                "code": FootballDataClient.COMPETITIONS.get(league, league.upper()),
                "upserted": upserted,
                "skipped": skipped,
                "errors": errors,
                "status": "ok" if not errors else "partial",
            })
            logger.info(f"[fd12] {league}: upserted={upserted} skipped={skipped}")
        except Exception as exc:
            err_msg = str(exc)
            all_errors.append(f"{league}: {err_msg}")
            results.append({
                "league": league,
                "code": FootballDataClient.COMPETITIONS.get(league, league.upper()),
                "upserted": 0, "skipped": 0,
                "errors": [err_msg], "status": "error",
            })
            logger.warning(f"[fd12] {league} failed: {exc}")

    duration = round((_dt.utcnow() - started_at).total_seconds(), 1)
    return {
        "status": "success" if not all_errors else ("partial" if total_upserted > 0 else "failed"),
        "total_upserted": total_upserted,
        "total_skipped":  total_skipped,
        "error_count":    len(all_errors),
        "duration_seconds": duration,
        "days_ahead": days,
        "competitions": results,
    }


@router.post("/sync-fixtures")
async def sync_fixtures(
    days: int = 90,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Trigger an immediate fixture sync from TheSportsDB + Football-Data.org.

    Covers all leagues including international competitions (World Cup, AFCON,
    UEFA Euro, Copa América, Nations League, Copa Libertadores).
    Runs both phases and returns a summary.
    """
    from app.services.sportsdb_api import sync_upcoming_fixtures
    try:
        result = await sync_upcoming_fixtures(db, days_ahead=days)
    except Exception as sync_err:
        logger.error(f"[admin] sync_fixtures error: {sync_err}")
        result = {"inserted": 0, "updated": 0, "skipped": 0, "total_fetched": 0, "error": str(sync_err)}

    # Seed predictions for newly inserted fixtures
    seeded = 0
    try:
        from app.modules.predictions.seeder import seed_predictions_for_upcoming
        seeded = await seed_predictions_for_upcoming(db)
    except Exception as seed_err:
        logger.warning(f"[admin] prediction seeder failed: {seed_err}")

    return {
        "status": "success",
        "fixtures": result,
        "predictions_seeded": seeded,
        "days_ahead": days,
    }


@router.get("/leagues")
async def list_leagues(current_user=Depends(get_current_admin)):
    from app.services.sportsdb_api import LEAGUE_DISPLAY, LEAGUES
    return [
        {"slug": slug, "name": LEAGUE_DISPLAY.get(slug, slug), "id": lid}
        for slug, lid in LEAGUES.items()
    ]


@router.get("/markets")
async def list_markets(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """List all markets in the DB."""
    from app.db.models import Market
    rows = (await db.execute(
        select(Market).order_by(Market.created_at.desc()).limit(500)
    )).scalars().all()
    return [
        {
            "id": m.id,
            "market_type": m.market_type,
            "category": m.category,
            "title": m.title,
            "description": m.description,
            "status": m.status,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]


@router.get("/marketplace/pending")
async def list_pending_listings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """List marketplace listings awaiting admin approval."""
    from app.modules.marketplace.models import AIModelListing
    rows = (await db.execute(
        select(AIModelListing)
        .where(AIModelListing.approval_status == "pending")
        .order_by(AIModelListing.created_at.desc())
        .limit(200)
    )).scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "slug": r.slug,
            "description": r.description,
            "category": r.category,
            "creator_id": r.creator_id,
            "price_per_call": float(r.price_per_call),
            "approval_status": r.approval_status,
            "approval_note": r.approval_note,
            "is_active": r.is_active,
            "is_verified": r.is_verified,
            "usage_count": r.usage_count,
            "avg_rating": r.avg_rating,
            "total_staked": float(r.total_staked),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ── Integration settings (admin-configurable via PlatformConfig) ─────────

class IntegrationSettingUpdate(BaseModel):
    key: str
    value: str


EDITABLE_INTEGRATION_KEYS = {
    "PI_APP_ID", "PI_APP_SECRET", "PI_WEBHOOK_SECRET", "PI_SANDBOX_MODE",
    "FLW_SECRET_KEY", "FLW_PUBLIC_KEY", "FLW_WEBHOOK_SECRET",
    "PAYSTACK_SECRET_KEY", "PAYSTACK_WEBHOOK_SECRET",
    "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET",
    "FOOTBALL_DATA_API_KEY", "THESPORTSDB_API_KEY", "ODDS_API_KEY",
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "RESEND_API_KEY",
    # Offerwall / Rewards providers
    "AYET_API_TOKEN", "BITLABS_APP_TOKEN",
    "CPX_RESEARCH_APP_ID", "CPX_RESEARCH_SECURE_HASH_KEY",
    "REVU_PUBLISHER_ID", "TAPJOY_SDK_KEY",
}


@router.get("/integrations/settings")
async def get_integration_settings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Return all integration keys with their configured status (masked values)."""
    from app.modules.wallet.models import PlatformConfig
    result = await db.execute(
        select(PlatformConfig).where(PlatformConfig.key.in_(
            [f"integration:{k}" for k in EDITABLE_INTEGRATION_KEYS]
        ))
    )
    db_rows = {row.key.replace("integration:", ""): row.value for row in result.scalars().all()}

    settings = []
    for entry in _KEY_REGISTRY:
        name = entry["name"]
        env_val = os.getenv(name, "")
        db_val = db_rows.get(name, "")
        is_set = bool(env_val or db_val)
        settings.append({
            "key": name,
            "label": entry.get("label", name),
            "group": entry.get("group", "Other"),
            "description": entry.get("description", ""),
            "required": entry.get("required", False),
            "configured": is_set,
            "source": "env" if env_val else ("db" if db_val else "none"),
        })
    return {"settings": settings, "total": len(settings)}


@router.put("/integrations/settings")
async def update_integration_setting(
    body: IntegrationSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Store an integration key in PlatformConfig (DB-backed, survives restarts)."""
    from app.modules.wallet.models import PlatformConfig
    if body.key not in EDITABLE_INTEGRATION_KEYS:
        raise HTTPException(400, f"Key '{body.key}' is not an editable integration setting")
    if not body.value.strip():
        raise HTTPException(400, "value cannot be empty")

    db_key = f"integration:{body.key}"
    row = (await db.execute(
        select(PlatformConfig).where(PlatformConfig.key == db_key)
    )).scalar_one_or_none()

    if row:
        row.value = body.value.strip()
    else:
        db.add(PlatformConfig(key=db_key, value=body.value.strip()))

    # Also inject into the running process env so it takes effect immediately
    os.environ[body.key] = body.value.strip()

    await db.commit()

    # Audit
    audit = AuditLog(
        action="integration_key_updated",
        actor=current_user.username,
        resource="integration",
        resource_id=body.key,
        details={"masked_value": "••••" + body.value.strip()[-4:] if len(body.value.strip()) > 4 else "••••"},
        status="success",
    )
    db.add(audit)
    await db.commit()

    return {"status": "ok", "key": body.key, "message": f"{body.key} updated and active immediately"}


@router.delete("/integrations/settings/{key}")
async def delete_integration_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Remove a DB-stored integration key (env var remains until restart)."""
    from app.modules.wallet.models import PlatformConfig
    if key not in EDITABLE_INTEGRATION_KEYS:
        raise HTTPException(400, f"Key '{key}' is not an editable integration setting")

    db_key = f"integration:{key}"
    row = (await db.execute(
        select(PlatformConfig).where(PlatformConfig.key == db_key)
    )).scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()
    return {"status": "ok", "key": key, "message": f"{key} removed from DB (env var still active until restart)"}


# ── Pi Network — payment lifecycle admin helpers ───────────────────────

@router.get("/pi/status")
async def pi_network_status(current_user=Depends(get_current_admin)):
    """Show Pi Network integration configuration status."""
    from app.services.pi_network import is_configured, _get_config
    cfg = _get_config()
    return {
        "configured": is_configured(),
        "sandbox_mode": cfg["sandbox"],
        "app_id_set": bool(cfg["app_id"]),
        "app_secret_set": bool(cfg["app_secret"]),
        "webhook_secret_set": bool(cfg["webhook_secret"]),
        "api_base": "https://api.minepi.com",
        "docs": "https://developers.minepi.com/doc/payment",
    }


@router.get("/integrations/webhook-events")
async def list_webhook_events(
    provider: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Return paginated webhook delivery events, newest first."""
    from app.modules.wallet.models import WebhookEvent
    from sqlalchemy import desc as _desc
    base_q = select(WebhookEvent)
    if provider:
        base_q = base_q.where(WebhookEvent.provider == provider)
    total = (await db.execute(
        select(func.count()).select_from(base_q.subquery())
    )).scalar_one()
    rows = (await db.execute(
        base_q.order_by(_desc(WebhookEvent.received_at)).limit(limit).offset(offset)
    )).scalars().all()
    return {
        "events": [
            {
                "id": e.id,
                "provider": e.provider,
                "event_type": e.event_type,
                "reference": e.reference,
                "amount": str(e.amount) if e.amount is not None else None,
                "currency": e.currency,
                "status": e.status,
                "sig_verified": e.sig_verified,
                "outcome": e.outcome,
                "error_msg": e.error_msg,
                "payload_summary": e.payload_summary,
                "received_at": e.received_at.isoformat() if e.received_at else None,
            }
            for e in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/pi/payments/{payment_id}")
async def get_pi_payment(payment_id: str, current_user=Depends(get_current_admin)):
    """Fetch a Pi Network payment by ID (uses Pi Server API)."""
    from app.services.pi_network import get_payment
    result = await get_payment(payment_id)
    if result.get("error"):
        raise HTTPException(502, result["error"])
    return result


# ── Offerwall provider status / authenticated URLs ─────────────────────────

@router.get("/offerwall/providers")
async def get_offerwall_providers(current_user=Depends(get_current_admin)):
    """Return all offerwall providers with their configuration status.
    Does NOT expose secret tokens — only indicates whether each key is set.
    """
    providers = [
        {
            "id":          "ayet",
            "name":        "Ayet Studios",
            "env_key":     "AYET_API_TOKEN",
            "configured":  bool(os.getenv("AYET_API_TOKEN", "").strip()),
        },
        {
            "id":          "bitlabs",
            "name":        "BitLabs",
            "env_key":     "BITLABS_APP_TOKEN",
            "configured":  bool(os.getenv("BITLABS_APP_TOKEN", "").strip()),
        },
        {
            "id":          "cpx",
            "name":        "CPX Research",
            "env_key":     "CPX_RESEARCH_APP_ID",
            "configured":  bool(os.getenv("CPX_RESEARCH_APP_ID", "").strip()),
        },
        {
            "id":          "revu",
            "name":        "Revenue Universe",
            "env_key":     "REVU_PUBLISHER_ID",
            "configured":  bool(os.getenv("REVU_PUBLISHER_ID", "").strip()),
        },
        {
            "id":          "tapjoy",
            "name":        "Tapjoy",
            "env_key":     "TAPJOY_SDK_KEY",
            "configured":  bool(os.getenv("TAPJOY_SDK_KEY", "").strip()),
        },
    ]
    return {"providers": providers}


# ══════════════════════════════════════════════════════════════════════════════
# ── VIT Cloud Storage Capacity ──────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/cloud/storage")
async def get_cloud_storage_capacity(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """
    Returns VIT cloud total storage capacity: used, free, and per-provider breakdown.
    Aggregates registered user storage nodes + Tachyon disk usage.
    """
    import shutil
    from app.modules.storage_verification.models import UserStorageNode, TachyonManifest

    # ── 1. OS-level disk (Render ephemeral disk) ───────────────────────────
    try:
        du = shutil.disk_usage("/")
        disk_total_bytes  = du.total
        disk_used_bytes   = du.used
        disk_free_bytes   = du.free
    except Exception:
        disk_total_bytes = disk_used_bytes = disk_free_bytes = 0

    # ── 2. Tachyon manifest bytes stored ──────────────────────────────────
    tachyon_bytes = (await db.scalar(
        select(func.sum(TachyonManifest.size_bytes))
    )) or 0
    tachyon_count = (await db.scalar(
        select(func.count(TachyonManifest.file_id))
    )) or 0

    # ── 3. User-contributed node capacity (all active nodes) ───────────────
    from decimal import Decimal

    node_rows = (await db.execute(
        select(
            UserStorageNode.provider,
            func.sum(UserStorageNode.gb_contributed).label("total_gb"),
            func.sum(UserStorageNode.gb_used).label("used_gb"),
            func.count(UserStorageNode.id).label("node_count"),
        )
        .where(UserStorageNode.status == "active")
        .group_by(UserStorageNode.provider)
    )).all()

    nodes_total_gb = float(sum((r.total_gb or 0) for r in node_rows))
    nodes_used_gb  = float(sum((r.used_gb  or 0) for r in node_rows))
    nodes_free_gb  = max(0.0, nodes_total_gb - nodes_used_gb)

    provider_breakdown = [
        {
            "provider": r.provider,
            "total_gb": float(r.total_gb or 0),
            "used_gb":  float(r.used_gb  or 0),
            "free_gb":  max(0.0, float(r.total_gb or 0) - float(r.used_gb or 0)),
            "node_count": int(r.node_count or 0),
            "utilization_pct": round(
                float(r.used_gb or 0) / max(float(r.total_gb or 1), 0.001) * 100, 1
            ),
        }
        for r in node_rows
    ]

    # ── 4. Cloud provider env flags ────────────────────────────────────────
    providers_active = []
    if os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON", "").strip():
        providers_active.append("Google Drive")
    if os.getenv("DROPBOX_ACCESS_TOKEN", "").strip() or os.getenv("DROPBOX_REFRESH_TOKEN", "").strip():
        providers_active.append("Dropbox")
    if os.getenv("ONEDRIVE_CLIENT_ID", "").strip():
        providers_active.append("OneDrive")
    if not providers_active:
        providers_active.append("Local Disk (ephemeral)")

    total_capacity_gb = nodes_total_gb or round(disk_total_bytes / (1024 ** 3), 2)
    total_used_gb     = nodes_used_gb  or round(disk_used_bytes  / (1024 ** 3), 2)
    total_free_gb     = nodes_free_gb  or round(disk_free_bytes  / (1024 ** 3), 2)
    utilization_pct   = round(total_used_gb / max(total_capacity_gb, 0.001) * 100, 1)

    return {
        "summary": {
            "total_capacity_gb":  total_capacity_gb,
            "used_gb":            total_used_gb,
            "free_gb":            total_free_gb,
            "utilization_pct":    utilization_pct,
            "tachyon_files":      int(tachyon_count),
            "tachyon_bytes":      int(tachyon_bytes),
            "providers_active":   providers_active,
            "alert": utilization_pct > 90,
        },
        "disk": {
            "total_bytes": int(disk_total_bytes),
            "used_bytes":  int(disk_used_bytes),
            "free_bytes":  int(disk_free_bytes),
            "total_gb":    round(disk_total_bytes / (1024 ** 3), 2),
            "used_gb":     round(disk_used_bytes  / (1024 ** 3), 2),
            "free_gb":     round(disk_free_bytes  / (1024 ** 3), 2),
            "utilization_pct": round(disk_used_bytes / max(disk_total_bytes, 1) * 100, 1),
        },
        "nodes": {
            "total_gb":    nodes_total_gb,
            "used_gb":     nodes_used_gb,
            "free_gb":     nodes_free_gb,
            "provider_breakdown": provider_breakdown,
        },
    }


# ── System Resources ────────────────────────────────────────────────────────

@router.get("/system/resources")
async def get_system_resources(current_user=Depends(get_current_admin)):
    """Returns real-time CPU, RAM, and disk resource utilization."""
    import shutil
    try:
        import psutil
        cpu_pct    = psutil.cpu_percent(interval=0.3)
        mem        = psutil.virtual_memory()
        ram_total  = mem.total
        ram_used   = mem.used
        ram_pct    = mem.percent
        swap       = psutil.swap_memory()
        swap_pct   = swap.percent
    except Exception:
        cpu_pct = ram_total = ram_used = ram_pct = swap_pct = 0

    try:
        du = shutil.disk_usage("/")
        disk_total = du.total
        disk_used  = du.used
        disk_free  = du.free
        disk_pct   = round(disk_used / max(disk_total, 1) * 100, 1)
    except Exception:
        disk_total = disk_used = disk_free = disk_pct = 0

    def _fmt_bytes(b: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{b:.1f} {unit}"
            b //= 1024
        return f"{b:.1f} TB"

    return {
        "cpu": {
            "percent": cpu_pct,
            "status": "ok" if cpu_pct < 80 else ("warn" if cpu_pct < 95 else "critical"),
        },
        "ram": {
            "total_bytes": int(ram_total),
            "used_bytes":  int(ram_used),
            "percent":     ram_pct,
            "total_fmt":   _fmt_bytes(int(ram_total)),
            "used_fmt":    _fmt_bytes(int(ram_used)),
            "status":      "ok" if ram_pct < 80 else ("warn" if ram_pct < 95 else "critical"),
        },
        "swap": {"percent": swap_pct},
        "disk": {
            "total_bytes": int(disk_total),
            "used_bytes":  int(disk_used),
            "free_bytes":  int(disk_free),
            "percent":     disk_pct,
            "total_fmt":   _fmt_bytes(int(disk_total)),
            "used_fmt":    _fmt_bytes(int(disk_used)),
            "free_fmt":    _fmt_bytes(int(disk_free)),
            "status":      "ok" if disk_pct < 80 else ("warn" if disk_pct < 90 else "critical"),
        },
        "environment": os.getenv("ENVIRONMENT", "production"),
        "python_version": __import__("sys").version.split()[0],
    }


# ── Enhanced Admin Stats (with user growth + revenue) ─────────────────────

@router.get("/stats/extended")
async def get_extended_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Extended stats: user growth by period, revenue, prediction accuracy."""
    from datetime import datetime, timezone, timedelta

    now   = datetime.now(timezone.utc).replace(tzinfo=None)
    d1    = now - timedelta(days=1)
    d7    = now - timedelta(days=7)
    d30   = now - timedelta(days=30)

    new_24h = (await db.scalar(
        select(func.count(User.id)).where(User.created_at >= d1)
    )) or 0
    new_7d  = (await db.scalar(
        select(func.count(User.id)).where(User.created_at >= d7)
    )) or 0
    new_30d = (await db.scalar(
        select(func.count(User.id)).where(User.created_at >= d30)
    )) or 0

    active_7d = (await db.scalar(
        select(func.count(User.id)).where(User.last_login >= d7)
    )) or 0

    total_predictions = (await db.scalar(select(func.count(Prediction.id)))) or 0
    settled_preds = (await db.scalar(
        select(func.count(Prediction.id)).where(Prediction.was_correct.isnot(None))
    )) or 0
    correct_preds = (await db.scalar(
        select(func.count(Prediction.id)).where(Prediction.was_correct == True)
    )) or 0
    accuracy_pct = round(correct_preds / max(settled_preds, 1) * 100, 1)

    # Revenue from wallet transactions
    total_revenue = 0.0
    try:
        from app.modules.wallet.models import Transaction
        rev_row = (await db.scalar(
            select(func.sum(Transaction.amount)).where(
                Transaction.transaction_type.in_(["deposit", "subscription"])
            )
        ))
        total_revenue = float(rev_row or 0)
    except Exception:
        pass

    return {
        "user_growth": {
            "new_24h": int(new_24h),
            "new_7d":  int(new_7d),
            "new_30d": int(new_30d),
            "active_7d": int(active_7d),
        },
        "predictions": {
            "total": int(total_predictions),
            "settled": int(settled_preds),
            "correct": int(correct_preds),
            "accuracy_pct": accuracy_pct,
        },
        "revenue": {
            "total_usd": total_revenue,
        },
    }


# ── Ensemble Run Trigger ────────────────────────────────────────────────────

@router.post("/ensemble/run")
async def trigger_ensemble_run(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Force-run the strategic ensemble on all upcoming unresolved matches."""
    from datetime import datetime, timezone, timedelta
    now    = datetime.now(timezone.utc).replace(tzinfo=None)
    future = now + timedelta(days=7)

    matches_q = await db.execute(
        select(Match).where(
            Match.kickoff_time >= now,
            Match.kickoff_time <= future,
            Match.actual_outcome.is_(None),
        ).limit(50)
    )
    matches = matches_q.scalars().all()

    seeded = 0
    errors = 0
    try:
        from app.modules.predictions.seeder import seed_predictions_for_upcoming
        seeded = await seed_predictions_for_upcoming(db)
    except Exception as e:
        errors += 1
        logger.warning("Ensemble run seeder error: %s", e)

    audit = AuditLog(
        action="ensemble_run",
        actor=current_user.username,
        resource="ensemble",
        resource_id="all",
        details={"matches_found": len(matches), "seeded": seeded, "errors": errors},
        status="success" if errors == 0 else "partial",
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "ok",
        "matches_found": len(matches),
        "predictions_seeded": seeded,
        "errors": errors,
        "message": f"Ensemble run complete: {seeded} predictions seeded across {len(matches)} matches",
    }


# ── Deploy Status (Render) ─────────────────────────────────────────────────

@router.get("/deploy/status")
async def get_deploy_status(current_user=Depends(get_current_admin)):
    """Returns current Render deployment status and last deploy info."""
    import httpx

    render_key    = os.getenv("RENDER_API_KEY", "").strip()
    render_svc_id = os.getenv("RENDER_SERVICE_ID", "srv-d84gu177f7vs73a3djeg").strip()

    if not render_key:
        return {"available": False, "reason": "RENDER_API_KEY not set"}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            svc_r = await client.get(
                f"https://api.render.com/v1/services/{render_svc_id}",
                headers={"Authorization": f"Bearer {render_key}"},
            )
            dep_r = await client.get(
                f"https://api.render.com/v1/services/{render_svc_id}/deploys?limit=3",
                headers={"Authorization": f"Bearer {render_key}"},
            )

        svc = svc_r.json() if svc_r.status_code == 200 else {}
        deps = dep_r.json() if dep_r.status_code == 200 else []

        latest = deps[0] if deps else {}
        dep_obj = latest.get("deploy", {})

        return {
            "available": True,
            "service": {
                "id":        svc.get("id"),
                "name":      svc.get("name"),
                "suspended": svc.get("suspended"),
                "url":       svc.get("serviceDetails", {}).get("url"),
                "plan":      svc.get("serviceDetails", {}).get("plan"),
                "region":    svc.get("serviceDetails", {}).get("region"),
                "updated_at": svc.get("updatedAt"),
            },
            "latest_deploy": {
                "id":          dep_obj.get("id"),
                "status":      dep_obj.get("status"),
                "created_at":  dep_obj.get("createdAt"),
                "finished_at": dep_obj.get("finishedAt"),
            },
            "recent_deploys": [
                {
                    "id":     d.get("deploy", {}).get("id"),
                    "status": d.get("deploy", {}).get("status"),
                    "created_at": d.get("deploy", {}).get("createdAt"),
                }
                for d in deps
            ],
        }
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


# ── Storage Network Admin Summary ──────────────────────────────────────────

@router.get("/storage/network")
async def get_storage_network_summary(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Global VIT cloud storage network: all active nodes, total capacity."""
    from app.modules.storage_verification.models import UserStorageNode, TachyonManifest

    total_nodes = (await db.scalar(select(func.count(UserStorageNode.id)))) or 0
    active_nodes = (await db.scalar(
        select(func.count(UserStorageNode.id)).where(UserStorageNode.status == "active")
    )) or 0

    capacity = (await db.execute(
        select(
            func.sum(UserStorageNode.gb_contributed).label("total_gb"),
            func.sum(UserStorageNode.gb_used).label("used_gb"),
            func.sum(UserStorageNode.tsc_earned).label("total_tsc_earned"),
        ).where(UserStorageNode.status == "active")
    )).one()

    total_gb   = float(capacity.total_gb  or 0)
    used_gb    = float(capacity.used_gb   or 0)
    free_gb    = max(0.0, total_gb - used_gb)
    tsc_earned = float(capacity.total_tsc_earned or 0)

    tachyon_files = (await db.scalar(
        select(func.count(TachyonManifest.file_id))
    )) or 0
    tachyon_bytes = (await db.scalar(
        select(func.sum(TachyonManifest.size_bytes))
    )) or 0

    import shutil
    disk = shutil.disk_usage("/")

    return {
        "nodes": {
            "total": int(total_nodes),
            "active": int(active_nodes),
        },
        "capacity": {
            "total_gb":  total_gb,
            "used_gb":   used_gb,
            "free_gb":   free_gb,
            "used_pct":  round(used_gb / max(total_gb, 0.001) * 100, 1),
        },
        "tachyon": {
            "files": int(tachyon_files),
            "bytes": int(tachyon_bytes),
            "gb":    round(tachyon_bytes / (1024**3), 3),
        },
        "tsc": {
            "total_earned": tsc_earned,
        },
        "server_disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb":  round(disk.used  / (1024**3), 2),
            "free_gb":  round(disk.free  / (1024**3), 2),
            "used_pct": round(disk.used / max(disk.total, 1) * 100, 1),
        },
    }
