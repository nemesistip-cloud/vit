"""
app/api/routes/registry.py — VIT Platform Service Registry

Phase 0 foundation: every frontend page and internal service discovers
peer service URLs from here instead of hardcoding them.

Routes:
  GET /api/registry   — canonical service URL map + live health
  GET /api/services   — alias kept for frontend compatibility
  GET /api/status     — cross-service health aggregator
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import APP_VERSION

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Registry"])


# ---------------------------------------------------------------------------
# Service URL configuration — override with env vars when moving services
# ---------------------------------------------------------------------------

def _url(key: str, default: str) -> str:
    return os.getenv(key, default).rstrip("/")


def _service_urls() -> dict[str, str]:
    return {
        "gateway":    _url("VIT_GATEWAY_URL",    "https://vitnetwork-nls4.onrender.com"),
        "ai":         _url("VIT_AI_URL",          "https://vit-ai.onrender.com"),
        "storage":    _url("VIT_STORAGE_URL",     "https://vit-storage-4trt.onrender.com"),
        "blockchain": _url("VIT_BLOCKCHAIN_URL",  "https://vitnetwork-nls4.onrender.com"),
        "wallet":     _url("VIT_WALLET_URL",      "https://vitnetwork-nls4.onrender.com"),
    }


# ---------------------------------------------------------------------------
# Health probe — one external service, with timeout
# ---------------------------------------------------------------------------

async def _probe(client: httpx.AsyncClient, name: str, base_url: str) -> dict[str, Any]:
    """Probe a service's operational endpoint and return a normalized status."""
    t0 = time.monotonic()
    try:
        # vit-ai's authoritative readiness contract is /api/v1/ai/status.
        # Keep the other service probes on their existing /health contracts.
        path = "/api/v1/ai/status" if name == "ai" else "/health"
        r = await client.get(f"{base_url}{path}", timeout=5.0)
        latency_ms = round((time.monotonic() - t0) * 1000)
        if r.status_code < 500:
            body: dict = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            status = body.get("status", "ok")
            if name == "ai" and status == "operational":
                status = "healthy"
            return {
                "status":     status,
                "version":    body.get("version"),
                "models_loaded": body.get("loaded_models_count", body.get("models_loaded")),
                "latency_ms": latency_ms,
                "reachable":  True,
            }
        return {"status": "degraded", "latency_ms": latency_ms, "reachable": True,
                "http_status": r.status_code}
    except httpx.TimeoutException:
        return {"status": "timeout", "latency_ms": 5000, "reachable": False}
    except Exception as exc:
        logger.warning("[registry] probe %s failed: %s", name, exc)
        return {"status": "unreachable", "latency_ms": None, "reachable": False}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/registry", summary="Service Registry")
@router.get("/services", include_in_schema=False)
async def get_registry() -> JSONResponse:
    """
    Return the canonical URL map for every service in the VIT ecosystem,
    together with a live health snapshot for each.

    Frontend pages must discover service URLs from this endpoint instead of
    hardcoding them.  When services move to a different host, update the
    VIT_*_URL environment variables — nothing else changes.
    """
    urls = _service_urls()

    async with httpx.AsyncClient() as client:
        probes = await asyncio.gather(
            _probe(client, "ai",      urls["ai"]),
            _probe(client, "storage", urls["storage"]),
        )

    ai_health, storage_health = probes

    services: dict[str, Any] = {}
    for name, url in urls.items():
        entry: dict[str, Any] = {"url": url}
        if name == "ai":
            entry.update(ai_health)
        elif name == "storage":
            entry.update(storage_health)
        else:
            entry["status"] = "ok"
        services[name] = entry

    overall = "healthy"
    if ai_health["status"] not in ("ok", "healthy", "starting") or \
       storage_health["status"] not in ("ok", "healthy", "quantum_stable", "starting"):
        overall = "degraded"

    return JSONResponse({
        "status":    overall,
        "version":   APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services":  services,
    })


@router.get("/status", summary="Cross-Service Health Aggregator")
async def get_platform_status() -> JSONResponse:
    """
    Aggregate live health across every VIT service (gateway subsystems +
    external vit-ai and vit-storage).  This is the single endpoint an
    ops dashboard or monitoring tool needs.
    """
    from app.core.kernel import kernel
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import text
    import redis.asyncio as aioredis

    urls = _service_urls()

    # --- Probe external services concurrently ---
    async with httpx.AsyncClient() as client:
        ai_probe, storage_probe = await asyncio.gather(
            _probe(client, "ai",      urls["ai"]),
            _probe(client, "storage", urls["storage"]),
        )

    # --- Local DB check ---
    db_status = "connected"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("[registry/status] DB probe failed: %s", exc)
        db_status = "disconnected"

    # --- Local Redis check ---
    redis_url = os.getenv("REDIS_URL", "")
    redis_status = "not_configured"
    if redis_url:
        try:
            r = aioredis.from_url(redis_url, socket_connect_timeout=2)
            await r.ping()
            await r.aclose()
            redis_status = "connected"
        except Exception as exc:
            logger.warning("[registry/status] Redis probe failed: %s", exc)
            redis_status = "disconnected"

    # --- Kernel subsystem summary ---
    kernel_info = kernel.get_status() if kernel else {}
    kernel_state = kernel_info.get("kernel_state", "UNKNOWN")

    # --- Overall status ---
    issues = sum([
        db_status != "connected",
        redis_status == "disconnected",
        not ai_probe["reachable"],
        not storage_probe["reachable"],
        kernel_state == "DEGRADED",
    ])
    if issues == 0:
        overall = "healthy"
    elif issues <= 2:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return JSONResponse({
        "status":    overall,
        "version":   APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "gateway": {
                "status":       "ok",
                "kernel_state": kernel_state,
                "uptime_s":     round(time.time() - getattr(kernel, "startup_time", time.time()), 1),
            },
            "ai":      ai_probe,
            "storage": storage_probe,
        },
        "infrastructure": {
            "database": {"status": db_status},
            "redis":    {"status": redis_status},
        },
    })
