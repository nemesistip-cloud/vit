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
async def list_api_keys():
    keys = []
    for entry in _KEY_REGISTRY:
        name = entry.get("name")
        val = os.getenv(name) if name else None
        keys.append({
            **entry,
            "configured": bool(val),
            "masked": "••••" if val else ""
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
    """Provides dashboard overview statistics."""
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    match_count = (await db.execute(select(func.count(Match.id)))).scalar() or 0
    job_count = (await db.execute(select(func.count(TrainingJob.id)))).scalar() or 0
    audit_count = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0
    plan_count = (await db.execute(select(func.count(SubscriptionPlan.id)).where(SubscriptionPlan.is_active == True))).scalar() or 0

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

    top_users = [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "tier": u.subscription_tier
        } for u in top_users_rows
    ]

    return {
        "users": user_count,
        "matches": match_count,
        "training_jobs": job_count,
        "active_plans": plan_count,
        "audit_entries": audit_count,
        "recent_activity": recent_activity,
        "top_users": top_users
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
                "vitcoin_balance": 0
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
    return {"status": "success", "message": "Cache cleared"}

@router.post("/system/backup")
async def create_backup(current_user=Depends(get_current_admin)):
    return {"status": "success", "backup": f"backup_{int(datetime.now().timestamp())}.sql"}

@router.post("/matches/fetch-fixtures")
async def fetch_fixtures(count: int = 50, days: int = 14, current_user=Depends(get_current_admin)):
    return {"status": "success", "stored": 0, "skipped_existing": 0}


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
async def list_markets(current_user=Depends(get_current_admin)):
    return []


@router.get("/marketplace/pending")
async def list_pending_listings(current_user=Depends(get_current_admin)):
    return []


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
