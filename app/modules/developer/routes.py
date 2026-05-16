# app/modules/developer/routes.py
"""Developer Platform REST API — Module L."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user, get_optional_user
from app.db.database import get_db
from app.db.models import User
from app.modules.developer import service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/developer", tags=["developer"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class CreateKeyRequest(BaseModel):
    name:       str           = Field(..., min_length=1, max_length=128)
    plan:       str           = Field(default="free")
    expires_at: Optional[datetime] = None


def _fmt_key(k, show_plain: bool = False) -> dict:
    return {
        "id":                       k.id,
        "name":                     k.name,
        "key_prefix":               k.key_prefix,
        "key":                      k.key_plain if show_plain else None,
        "plan":                     k.plan,
        "rate_limit_rpm":           k.rate_limit_rpm,
        "rate_limit_rpd":           k.rate_limit_rpd,
        "is_active":                k.is_active,
        "total_requests":           k.total_requests,
        "total_vitcoin_billed":     str(k.total_vitcoin_billed),
        "last_used_at":             k.last_used_at.isoformat() if k.last_used_at else None,
        "created_at":               k.created_at.isoformat() if k.created_at else None,
        "expires_at":               k.expires_at.isoformat() if k.expires_at else None,
    }


def _fmt_log(log) -> dict:
    return {
        "id":             log.id,
        "endpoint":       log.endpoint,
        "method":         log.method,
        "status_code":    log.status_code,
        "latency_ms":     log.latency_ms,
        "vitcoin_billed": str(log.vitcoin_billed),
        "called_at":      log.called_at.isoformat() if log.called_at else None,
    }


def _fmt_plan(p) -> dict:
    return {
        "name":                    p.name,
        "display_name":            p.display_name,
        "rate_limit_rpm":          p.rate_limit_rpm,
        "rate_limit_rpd":          p.rate_limit_rpd,
        "price_vitcoin_per_1k":    f"{float(p.price_vitcoin_per_1k):.2f}",
        "description":             p.description,
    }


# ── Plans ─────────────────────────────────────────────────────────────────────

@router.get("/plans", summary="List available API plans")
async def list_plans(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_optional_user),
):
    await svc.seed_plans(db)
    plans = await svc.list_plans(db)
    return [_fmt_plan(p) for p in plans]


# ── API Keys ──────────────────────────────────────────────────────────────────

@router.get("/keys", summary="List my API keys")
async def list_keys(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    keys = await svc.list_keys(db, current_user.id)
    return [_fmt_key(k) for k in keys]


@router.post("/keys", summary="Create a new API key", status_code=201)
async def create_key(
    body:         CreateKeyRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    try:
        key, raw = await svc.create_key(
            db,
            user_id=current_user.id,
            name=body.name,
            plan=body.plan,
            expires_at=body.expires_at,
        )
        result = _fmt_key(key, show_plain=True)
        result["key"] = raw   # shown only once
        # Clear stored plain key
        key.key_plain = None
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/keys/{key_id}", summary="Delete an API key")
async def delete_key(
    key_id:       int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    ok = await svc.delete_key(db, key_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"deleted": True, "key_id": key_id}


@router.patch("/keys/{key_id}/revoke", summary="Revoke (disable) an API key")
async def revoke_key(
    key_id:       int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    ok = await svc.revoke_key(db, key_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"revoked": True, "key_id": key_id}


# ── Usage ─────────────────────────────────────────────────────────────────────

@router.post("/keys/{key_id}/bill", summary="Bill one API call against a key (internal use)")
async def bill_key_call(
    key_id:       int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    G09: Deduct VITCoin for a single billable API call on the given key.
    Returns {allowed, reason}. Returns 402 if insufficient balance.
    """
    key = await svc.get_key(db, key_id, current_user.id)
    if not key or not key.is_active:
        raise HTTPException(status_code=404, detail="API key not found or inactive")

    allowed, reason = await svc.bill_api_call(db, key.id, current_user.id, key.plan)
    if not allowed:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient VITCoin balance to make API calls on the '{key.plan}' plan.",
        )
    return {"allowed": True, "reason": reason, "key_id": key_id, "plan": key.plan}


@router.get("/usage", summary="My recent API call history")
async def my_usage(
    limit:        int = Query(default=100, ge=1, le=500),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    logs = await svc.my_usage(db, current_user.id, limit=limit)
    return [_fmt_log(log) for log in logs]


@router.get("/usage/summary", summary="My API usage summary")
async def usage_summary(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await svc.usage_summary(db, current_user.id)


@router.get("/config/download", summary="Download my API configuration")
async def download_config(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """Return a JSON configuration of all active API keys and their limits."""
    keys = await svc.list_keys(db, current_user.id)
    active_keys = [k for k in keys if k.is_active]

    config = {
        "user_id": current_user.id,
        "generated_at": datetime.now().isoformat(),
        "api_keys": [
            {
                "name": k.name,
                "prefix": k.key_prefix,
                "plan": k.plan,
                "limits": {
                    "rpm": k.rate_limit_rpm,
                    "rpd": k.rate_limit_rpd
                }
            } for k in active_keys
        ]
    }
    return config


# ── Docs (stub endpoint returning SDK links) ──────────────────────────────────

@router.get("/docs", summary="Developer documentation links")
async def developer_docs(
    request: Request,
    _=Depends(get_optional_user),
):
    """Return developer reference docs.

    Endpoints are introspected from the live FastAPI app so the list always
    reflects what the server actually exposes — no hand-maintained snippets.
    """
    app = request.app
    seen: set[tuple[str, str]] = set()
    endpoints: list[dict] = []

    EXCLUDE_PREFIXES = (
        "/openapi", "/docs", "/redoc", "/static", "/assets", "/favicon",
        "/__", "/api/dev/admin",  # admin/dev internals
    )

    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if not path or not methods:
            continue
        if any(path.startswith(p) for p in EXCLUDE_PREFIXES):
            continue
        # Skip websocket / mount routes
        if any(m in {"HEAD", "OPTIONS"} for m in methods):
            methods = {m for m in methods if m not in {"HEAD", "OPTIONS"}}
        if not methods:
            continue

        summary = getattr(route, "summary", None) or ""
        tags = getattr(route, "tags", None) or []
        for method in sorted(methods):
            key = (method, path)
            if key in seen:
                continue
            seen.add(key)
            endpoints.append({
                "method":      method,
                "path":        path,
                "description": summary,
                "tags":        list(tags),
            })

    endpoints.sort(key=lambda e: (e["path"], e["method"]))

    return {
        "openapi_url":         "/openapi.json",
        "redoc_url":           "/redoc",
        "swagger_url":         "/docs",
        "sdk_typescript_url":  "https://github.com/vit-network/typescript-sdk",
        "sdk_python_url":      "https://github.com/vit-network/python-sdk",
        "base_api_url":        "/api",
        "authentication":      "Include your API key in the `X-API-Key` header.",
        "rate_limiting":       "Rate limits are enforced per minute and per day per key.",
        "endpoint_count":      len(endpoints),
        "endpoints":           endpoints,
    }


# ── Platform stats (admin) ────────────────────────────────────────────────────

@router.get("/endpoints", summary="List all public API endpoints")
async def list_endpoints():
    """Return a structured list of all public VIT API endpoints for discovery."""
    return {
        "version": "6.0",
        "base_url": "/api",
        "categories": {
            "matches": [
                "GET /matches/upcoming", "GET /matches/explore", "GET /matches/{id}",
                "GET /matches/{id}/predictions",
            ],
            "predictions": [
                "GET /history/picks", "GET /history/results-comparison",
                "GET /history/ticket/markets", "GET /history/ticket/build",
            ],
            "analytics": [
                "GET /analytics/summary", "GET /analytics/accuracy",
                "GET /analytics/leaderboard/validators", "GET /analytics/leaderboard/users",
            ],
            "wallet": [
                "GET /api/wallet/balance", "POST /api/wallet/deposit",
                "GET /api/wallet/vitcoin-price", "GET /api/wallet/exchange-rates",
            ],
            "marketplace": [
                "GET /api/marketplace/models", "GET /api/marketplace/stats",
                "GET /api/marketplace/leaderboard", "POST /api/marketplace/models",
            ],
            "governance": [
                "GET /api/governance/proposals", "GET /api/governance/stats",
                "POST /api/governance/proposals",
            ],
            "chain": [
                "GET /api/chain/stats", "GET /api/chain/blocks",
                "POST /api/chain/mint", "POST /api/chain/transfer",
            ],
            "developer": [
                "GET /api/developer/plans", "GET /api/developer/keys",
                "POST /api/developer/keys", "GET /api/developer/usage",
                "GET /api/developer/docs", "GET /api/developer/endpoints",
            ],
            "ai_assistant": [
                "GET /ai/assistant/status", "POST /ai/assistant/chat",
            ],
            "odds": [
                "GET /odds/injuries", "GET /odds/audit-log",
                "GET /odds/markets", "GET /odds/compare",
            ],
        },
        "authentication": "Bearer JWT or X-API-Key header (developer keys start with vit_)",
        "rate_limits": "60 req/min unauthenticated, 200 req/min authenticated",
    }


@router.get("/admin/stats", summary="Admin: developer platform statistics")
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    _:  User         = Depends(get_current_admin),
):
    return await svc.platform_stats(db)
