# app/modules/enterprise/routes.py
"""
Enterprise API, Data Licensing & Webhooks — Phase VIII / IX
Endpoints: API key management, usage metering, data bundle licensing,
           webhook registration and delivery log, rate-limit tiers.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, HttpUrl

from app.api.deps import get_current_user, get_current_admin
from app.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/enterprise", tags=["Enterprise"])

# ── In-memory stores ──────────────────────────────────────────────────────────
_API_KEYS:   Dict[str, dict] = {}   # key_id → key record
_WEBHOOKS:   Dict[str, dict] = {}   # hook_id → hook record
_HOOK_LOGS:  Dict[str, List] = {}   # hook_id → [delivery, ...]
_USAGE:      Dict[str, List] = {}   # key_id → [usage event, ...]

# ── Plans ─────────────────────────────────────────────────────────────────────
ENTERPRISE_PLANS = [
    {
        "id":               "starter",
        "name":             "Starter",
        "price_usd_month":  199,
        "requests_per_min": 60,
        "daily_limit":      10_000,
        "features":         ["REST API", "Match data", "Basic analytics", "Email support"],
        "webhooks":         2,
        "data_bundles":     ["matches", "odds"],
    },
    {
        "id":               "professional",
        "name":             "Professional",
        "price_usd_month":  799,
        "requests_per_min": 300,
        "daily_limit":      100_000,
        "features":         ["REST + WS API", "Full predictions", "Model comparison", "Priority support", "Custom webhooks"],
        "webhooks":         10,
        "data_bundles":     ["matches", "odds", "predictions", "analytics"],
    },
    {
        "id":               "enterprise",
        "name":             "Enterprise",
        "price_usd_month":  None,  # Contact sales
        "requests_per_min": 2000,
        "daily_limit":      None,  # Unlimited
        "features":         ["Unlimited API", "Raw model outputs", "Data licensing", "Dedicated SLA", "Custom integration"],
        "webhooks":         100,
        "data_bundles":     ["matches", "odds", "predictions", "analytics", "raw_model", "historical_5y"],
    },
]


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateAPIKey(BaseModel):
    name:        str = Field(..., min_length=1, max_length=80)
    plan:        str = Field(default="starter", description="starter | professional | enterprise")
    description: str = Field(default="", max_length=500)
    ip_whitelist: List[str] = Field(default_factory=list)


class WebhookCreate(BaseModel):
    url:        str         = Field(..., description="HTTPS endpoint to receive events")
    events:     List[str]   = Field(..., min_length=1,
                                    description="prediction.settled | match.result | odds.update | user.stake | defi.yield")
    secret:     Optional[str] = Field(None, description="If provided, used for HMAC signature header")
    name:       str          = Field(default="", max_length=80)
    active:     bool         = Field(default=True)


class DataLicenseRequest(BaseModel):
    bundle:     str = Field(..., description="matches | odds | predictions | analytics | raw_model | historical_5y")
    usage_type: str = Field(default="internal", description="internal | commercial | resale")
    duration_days: int = Field(default=30, ge=1, le=365)


# ── API Key management ────────────────────────────────────────────────────────

@router.post("/api-keys", summary="Create enterprise API key")
async def create_api_key(body: CreateAPIKey, me: User = Depends(get_current_user)):
    plan = next((p for p in ENTERPRISE_PLANS if p["id"] == body.plan), None)
    if not plan:
        raise HTTPException(400, f"Invalid plan '{body.plan}'")

    raw_key = f"vit_{secrets.token_urlsafe(32)}"
    key_id  = str(uuid.uuid4())
    record = {
        "id":           key_id,
        "user_id":      me.id,
        "name":         body.name,
        "description":  body.description,
        "plan":         body.plan,
        "key_preview":  raw_key[:12] + "…",
        "ip_whitelist": body.ip_whitelist,
        "created_at":   time.time(),
        "last_used_at": None,
        "status":       "active",
        "requests_today": 0,
        "daily_limit":  plan["daily_limit"],
        "rpm_limit":    plan["requests_per_min"],
    }
    _API_KEYS[key_id] = record
    logger.info("enterprise:api-key created user=%s plan=%s", me.id, body.plan)
    # Return key ONCE — not stored
    return {**record, "key": raw_key, "warning": "Store this key securely — it is shown once."}


@router.get("/api-keys", summary="List my API keys")
async def list_api_keys(me: User = Depends(get_current_user)):
    keys = [k for k in _API_KEYS.values() if k["user_id"] == me.id]
    # Never return raw key — only preview
    return {"keys": keys, "total": len(keys)}


@router.delete("/api-keys/{key_id}", summary="Revoke an API key")
async def revoke_api_key(key_id: str, me: User = Depends(get_current_user)):
    rec = _API_KEYS.get(key_id)
    if not rec or rec["user_id"] != me.id:
        raise HTTPException(404, "Key not found")
    rec["status"] = "revoked"
    return {"ok": True, "revoked": key_id}


@router.get("/api-keys/{key_id}/usage", summary="Usage stats for an API key")
async def key_usage(key_id: str, me: User = Depends(get_current_user)):
    rec = _API_KEYS.get(key_id)
    if not rec or rec["user_id"] != me.id:
        raise HTTPException(404, "Key not found")
    usage_log = _USAGE.get(key_id, [])
    total = len(usage_log)
    endpoints: dict[str, int] = {}
    for event in usage_log:
        ep = event.get("endpoint", "unknown")
        endpoints[ep] = endpoints.get(ep, 0) + 1
    return {
        "key_id":          key_id,
        "requests_total":  total,
        "requests_today":  rec["requests_today"],
        "daily_limit":     rec["daily_limit"],
        "top_endpoints":   sorted(endpoints.items(), key=lambda x: -x[1])[:10],
    }


# ── Webhooks ──────────────────────────────────────────────────────────────────

VALID_EVENTS = {
    "prediction.settled", "match.result", "odds.update",
    "user.stake", "defi.yield", "inplay.bet", "governance.vote"
}


@router.post("/webhooks", summary="Register a webhook")
async def create_webhook(body: WebhookCreate, me: User = Depends(get_current_user)):
    invalid = set(body.events) - VALID_EVENTS
    if invalid:
        raise HTTPException(400, f"Unknown events: {invalid}. Valid: {VALID_EVENTS}")
    hook_id = str(uuid.uuid4())
    hook = {
        "id":         hook_id,
        "user_id":    me.id,
        "url":        body.url,
        "events":     body.events,
        "name":       body.name,
        "active":     body.active,
        "secret":     body.secret,
        "created_at": time.time(),
        "success_count": 0,
        "failure_count": 0,
    }
    _WEBHOOKS[hook_id] = hook
    return {k: v for k, v in hook.items() if k != "secret"}   # never echo secret


@router.get("/webhooks", summary="List my webhooks")
async def list_webhooks(me: User = Depends(get_current_user)):
    hooks = [{k: v for k, v in h.items() if k != "secret"}
             for h in _WEBHOOKS.values() if h["user_id"] == me.id]
    return {"webhooks": hooks, "total": len(hooks)}


@router.patch("/webhooks/{hook_id}", summary="Update webhook (active toggle)")
async def update_webhook(hook_id: str, active: bool, me: User = Depends(get_current_user)):
    hook = _WEBHOOKS.get(hook_id)
    if not hook or hook["user_id"] != me.id:
        raise HTTPException(404, "Webhook not found")
    hook["active"] = active
    return {"ok": True, "hook_id": hook_id, "active": active}


@router.delete("/webhooks/{hook_id}", summary="Delete a webhook")
async def delete_webhook(hook_id: str, me: User = Depends(get_current_user)):
    hook = _WEBHOOKS.get(hook_id)
    if not hook or hook["user_id"] != me.id:
        raise HTTPException(404, "Webhook not found")
    del _WEBHOOKS[hook_id]
    _HOOK_LOGS.pop(hook_id, None)
    return {"ok": True}


@router.get("/webhooks/{hook_id}/logs", summary="Webhook delivery log")
async def webhook_logs(hook_id: str, limit: int = Query(50, ge=1, le=200), me: User = Depends(get_current_user)):
    hook = _WEBHOOKS.get(hook_id)
    if not hook or hook["user_id"] != me.id:
        raise HTTPException(404, "Webhook not found")
    logs = _HOOK_LOGS.get(hook_id, [])
    return {"hook_id": hook_id, "logs": logs[-limit:][::-1]}


@router.post("/webhooks/{hook_id}/test", summary="Send a test event to a webhook")
async def test_webhook(hook_id: str, background: BackgroundTasks, me: User = Depends(get_current_user)):
    hook = _WEBHOOKS.get(hook_id)
    if not hook or hook["user_id"] != me.id:
        raise HTTPException(404, "Webhook not found")

    async def _deliver():
        import aiohttp, json
        payload = {
            "event": "webhook.test",
            "timestamp": time.time(),
            "hook_id": hook_id,
            "data": {"message": "This is a VIT Network test event"},
        }
        log_entry = {"sent_at": time.time(), "event": "webhook.test", "status": "pending"}
        try:
            async with aiohttp.ClientSession() as sess:
                headers = {"Content-Type": "application/json", "X-VIT-Event": "webhook.test"}
                if hook.get("secret"):
                    sig = hmac.new(hook["secret"].encode(), json.dumps(payload).encode(), hashlib.sha256).hexdigest()
                    headers["X-VIT-Signature"] = f"sha256={sig}"
                async with sess.post(hook["url"], json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    log_entry["status"] = "success" if r.status < 400 else "failed"
                    log_entry["http_status"] = r.status
                    hook["success_count" if r.status < 400 else "failure_count"] += 1
        except Exception as exc:
            log_entry["status"] = "error"
            log_entry["error"]  = str(exc)
            hook["failure_count"] += 1
        _HOOK_LOGS.setdefault(hook_id, []).append(log_entry)

    background.add_task(_deliver)
    return {"ok": True, "message": "Test event dispatched"}


# ── Data Licensing ────────────────────────────────────────────────────────────

DATA_BUNDLES = {
    "matches":        {"name": "Match Data",         "records_per_day": 500,   "price_usd": 49},
    "odds":           {"name": "Live Odds",           "records_per_day": 5000,  "price_usd": 149},
    "predictions":    {"name": "AI Predictions",      "records_per_day": 500,   "price_usd": 299},
    "analytics":      {"name": "Analytics Export",    "records_per_day": 2000,  "price_usd": 199},
    "raw_model":      {"name": "Raw Model Outputs",   "records_per_day": 500,   "price_usd": 999},
    "historical_5y":  {"name": "5-Year Historical",   "records_per_day": 10000, "price_usd": 499},
}


@router.get("/data-bundles", summary="Available data licensing bundles")
async def list_data_bundles():
    return {"bundles": [{"id": k, **v} for k, v in DATA_BUNDLES.items()]}


@router.post("/data-licenses", summary="Request a data license")
async def request_license(body: DataLicenseRequest, me: User = Depends(get_current_user)):
    bundle = DATA_BUNDLES.get(body.bundle)
    if not bundle:
        raise HTTPException(400, f"Unknown bundle '{body.bundle}'")
    license_record = {
        "id":          str(uuid.uuid4()),
        "user_id":     me.id,
        "bundle":      body.bundle,
        "bundle_name": bundle["name"],
        "usage_type":  body.usage_type,
        "duration_days": body.duration_days,
        "price_usd":   bundle["price_usd"] * (body.duration_days / 30),
        "status":      "pending_payment",
        "created_at":  time.time(),
        "expires_at":  time.time() + body.duration_days * 86400,
    }
    return {"license": license_record, "next_step": "Complete payment via /api/wallet to activate."}


# ── Plans ─────────────────────────────────────────────────────────────────────

@router.get("/plans", summary="Enterprise API plan tiers")
async def list_plans():
    return {"plans": ENTERPRISE_PLANS}


# ── Admin usage overview ──────────────────────────────────────────────────────

@router.get("/admin/overview", summary="Admin: global enterprise usage overview", include_in_schema=False)
async def admin_overview(me: User = Depends(get_current_admin)):
    total_keys    = len(_API_KEYS)
    active_keys   = sum(1 for k in _API_KEYS.values() if k["status"] == "active")
    total_hooks   = len(_WEBHOOKS)
    total_requests = sum(len(v) for v in _USAGE.values())
    return {
        "total_api_keys":    total_keys,
        "active_api_keys":   active_keys,
        "total_webhooks":    total_hooks,
        "total_api_requests": total_requests,
    }
