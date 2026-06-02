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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_env, APP_VERSION, AUTH_ENABLED, API_KEY
from app.db.database import AsyncSessionLocal, get_db
from app.db.models import User, AuditLog, Match, Prediction, SubscriptionPlan
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

        _status("BASE_RPC_URL",           "Base L2 RPC",         required=False),
        _status("VIT_CONTRACT_ADDRESS",   "VITCoin Contract",    required=False),
        _status("REDIS_URL",              "Redis",               required=False),
        _status("SMTP_HOST",              "Email / SMTP",        required=False),
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
