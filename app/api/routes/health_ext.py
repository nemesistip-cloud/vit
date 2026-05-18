"""app/api/routes/health_ext.py — Extended health + Prometheus-style metrics.

GET /health/db       — Database connectivity check
GET /health/redis    — Redis connectivity check
GET /health/agents   — Agent health check
GET /metrics         — Prometheus-compatible metrics (text/plain)
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

_START_TIME = time.time()


@router.get("/health/db")
async def health_db():
    """Verify database connectivity with a lightweight ping."""
    try:
        from app.db.database import engine
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {
            "status":       "ok",
            "component":    "database",
            "checked_at":   datetime.now(timezone.utc).isoformat(),
            "latency_ms":   None,
        }
    except Exception as exc:
        logger.error("[health/db] database ping failed: %s", exc)
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"Database unreachable: {exc}")


@router.get("/health/redis")
async def health_redis():
    """Verify Redis connectivity (if REDIS_URL is configured)."""
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        return {
            "status":    "disabled",
            "component": "redis",
            "note":      "REDIS_URL not set — in-memory fallback active",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    try:
        import aioredis
        client = aioredis.from_url(redis_url, socket_connect_timeout=5)
        await client.ping()
        await client.close()
        return {
            "status":    "ok",
            "component": "redis",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except ImportError:
        return {
            "status":    "disabled",
            "component": "redis",
            "note":      "aioredis not installed — in-memory fallback active",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"Redis unreachable: {exc}")


@router.get("/health/agents")
async def health_agents():
    """Agent health summary."""
    try:
        from app.core.swarm_orchestrator import get_swarm
        swarm = get_swarm()
        if not swarm:
            return {"status": "starting", "note": "SwarmOrchestrator not yet initialised"}
        summary = swarm.health_summary()
        running = summary.get("running", 0)
        total   = summary.get("total", 22)
        ok      = running == total
        return {
            "status":    "ok" if ok else "degraded",
            "running":   running,
            "total":     total,
            "summary":   summary,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "status":  "error",
            "detail":  str(exc),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint.
    Format: metric_name{labels} value timestamp_ms
    """
    try:
        lines = []
        now_ms = int(time.time() * 1000)
        uptime = time.time() - _START_TIME

        # App info
        lines.append('# HELP vit_up Application uptime indicator (1 = running)')
        lines.append('# TYPE vit_up gauge')
        lines.append(f'vit_up 1 {now_ms}')

        lines.append('# HELP vit_uptime_seconds Seconds since application start')
        lines.append('# TYPE vit_uptime_seconds counter')
        lines.append(f'vit_uptime_seconds {uptime:.1f} {now_ms}')

        # DB stats
        try:
            from app.db.database import engine
            from sqlalchemy import text
            async with engine.begin() as conn:
                # Predictions
                res = await conn.execute(text("SELECT COUNT(*) FROM predictions"))
                pred_count = res.scalar() or 0
                lines.append('# HELP vit_predictions_total Total number of predictions in DB')
                lines.append('# TYPE vit_predictions_total counter')
                lines.append(f'vit_predictions_total {pred_count} {now_ms}')

                # Users
                res2 = await conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count = res2.scalar() or 0
                lines.append('# HELP vit_users_total Total registered users')
                lines.append('# TYPE vit_users_total counter')
                lines.append(f'vit_users_total {user_count} {now_ms}')

                # Settled predictions
                res3 = await conn.execute(text(
                    "SELECT COUNT(*) FROM predictions WHERE was_correct IS NOT NULL"
                ))
                settled = res3.scalar() or 0
                lines.append('# HELP vit_predictions_settled Settled (resolved) predictions')
                lines.append('# TYPE vit_predictions_settled counter')
                lines.append(f'vit_predictions_settled {settled} {now_ms}')

                # Correct predictions
                res4 = await conn.execute(text(
                    "SELECT COUNT(*) FROM predictions WHERE was_correct = true"
                ))
                correct = res4.scalar() or 0
                lines.append('# HELP vit_predictions_correct Correct settled predictions')
                lines.append('# TYPE vit_predictions_correct counter')
                lines.append(f'vit_predictions_correct {correct} {now_ms}')

        except Exception as db_exc:
            lines.append(f'# DB stats unavailable: {db_exc}')

        # Agent stats
        try:
            from app.core.swarm_orchestrator import get_swarm
            swarm = get_swarm()
            if swarm:
                h = swarm.health_summary()
                running = h.get("running", 0)
                total   = h.get("total", 22)
                lines.append('# HELP vit_agents_running Number of running agents')
                lines.append('# TYPE vit_agents_running gauge')
                lines.append(f'vit_agents_running {running} {now_ms}')
                lines.append('# HELP vit_agents_total Total configured agents')
                lines.append('# TYPE vit_agents_total gauge')
                lines.append(f'vit_agents_total {total} {now_ms}')
        except Exception:
            pass

        # Model stats
        try:
            from app.core.dependencies import get_orchestrator
            orch = get_orchestrator()
            if orch:
                status = orch.get_model_status()
                total_models = status.get("total", 0)
                ready_models = status.get("ready", 0)
                lines.append('# HELP vit_models_total Total configured ML models')
                lines.append('# TYPE vit_models_total gauge')
                lines.append(f'vit_models_total {total_models} {now_ms}')
                lines.append('# HELP vit_models_ready Models ready for inference')
                lines.append('# TYPE vit_models_ready gauge')
                lines.append(f'vit_models_ready {ready_models} {now_ms}')
        except Exception:
            pass

        return "\n".join(lines) + "\n"

    except Exception as exc:
        logger.error("[metrics] error: %s", exc)
        return f"# error generating metrics: {exc}\nvit_up 0\n"
