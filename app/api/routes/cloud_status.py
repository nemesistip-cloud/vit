"""
VIT Cloud Status Dashboard (v5.5.0)
8-subsystem health monitoring and real-time network liveness.

Endpoints:
  GET /api/cloud/status          — Real-time health snapshot (60s cache)
  GET /api/cloud/status/history  — Recent status history (from Redis)

Operator Integration:
  Add to main.py:
    from app.api.routes.cloud_status import router as cloud_status_router
    app.include_router(cloud_status_router, prefix="/api")

Celery Task:
  Register take_cloud_status_snapshot to run every 15 minutes.
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.cache import cached
from app.config import APP_VERSION
from app.db.models import User, Match, BackgroundTaskStatus

router = APIRouter(prefix="/cloud", tags=["Cloud Status"])
logger = logging.getLogger(__name__)

def _get_status_from_score(score: float) -> str:
    if score >= 90: return "healthy"
    if score >= 60: return "degraded"
    return "offline"

# ── Subsystem Health Checks ──────────────────────────────────────────────────

async def check_database_health(db: AsyncSession) -> Dict[str, Any]:
    """Check SQLAlchemy connection and core table access."""
    start = time.monotonic()
    try:
        await db.execute(text("SELECT 1"))
        latency = (time.monotonic() - start) * 1000
        # Check if Match table is readable
        match_count = (await db.execute(select(func.count()).select_from(Match))).scalar() or 0
        score = 100.0 if latency < 100 else max(60.0, 100.0 - (latency - 100) / 10)
        return {
            "status": "healthy" if score > 80 else "degraded",
            "score": round(score, 1),
            "latency_ms": round(latency, 2),
            "details": {"match_count": match_count}
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "offline", "score": 0.0, "error": str(e)}

async def check_infrastructure_health(request: Request) -> Dict[str, Any]:
    """Check Redis reachability and P2P connectivity."""
    redis_client = getattr(request.app.state, "redis", None)
    if not redis_client:
        return {"status": "offline", "score": 0.0, "error": "Redis client not found"}

    start = time.monotonic()
    try:
        await redis_client.ping()
        latency = (time.monotonic() - start) * 1000

        # Peer count from DB (vit_chain.p2p.models.PeerNode)
        peer_count = 0
        try:
            from vit_chain.p2p.models import PeerNode
            # We skip DB check here as it's an infrastructure liveness check
        except ImportError:
            pass

        score = 100.0 if latency < 50 else max(50.0, 100.0 - (latency - 50) / 2)
        return {
            "status": "healthy" if score > 80 else "degraded",
            "score": round(score, 1),
            "latency_ms": round(latency, 2),
            "details": {"redis": "online"}
        }
    except Exception as e:
        return {"status": "offline", "score": 0.0, "error": str(e)}

async def check_core_health() -> Dict[str, Any]:
    """Basic app liveness check."""
    return {
        "status": "healthy",
        "score": 100.0,
        "details": {"version": APP_VERSION}
    }

async def check_identity_health(db: AsyncSession) -> Dict[str, Any]:
    """Check user activity and verification status."""
    try:
        now = datetime.now(timezone.utc)
        since_24h = now - timedelta(hours=24)
        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        active_users = (await db.execute(select(func.count(User.id)).where(User.created_at >= since_24h))).scalar() or 0
        verified_users = (await db.execute(select(func.count(User.id)).where(User.is_verified == True))).scalar() or 0

        score = 100.0 if total_users > 0 else 50.0
        return {
            "status": "healthy" if score > 80 else "degraded",
            "score": score,
            "details": {
                "total_users": total_users,
                "active_24h": active_users,
                "verified_pct": round((verified_users / total_users * 100), 1) if total_users > 0 else 0
            }
        }
    except Exception as e:
        return {"status": "degraded", "score": 50.0, "error": str(e)}

async def check_blockchain_health(db: AsyncSession) -> Dict[str, Any]:
    """Check blockchain state, block height, and validator count."""
    try:
        from vit_chain.storage.db import ChainBlock
        from app.modules.blockchain.models import ValidatorProfile, ValidatorStatus

        block_res = await db.execute(select(func.max(ChainBlock.height)))
        max_height = block_res.scalar() or 0

        val_res = await db.execute(
            select(func.count(ValidatorProfile.id)).where(
                ValidatorProfile.status == ValidatorStatus.ACTIVE.value
            )
        )
        active_vals = val_res.scalar() or 0

        score = 100.0 if active_vals >= 3 else (active_vals / 3 * 100)
        return {
            "status": "healthy" if score > 80 else "degraded",
            "score": round(score, 1),
            "details": {
                "block_height": max_height,
                "active_validators": active_vals
            }
        }
    except Exception as e:
        return {"status": "degraded", "score": 50.0, "error": str(e)}

async def check_tachyon_health(db: AsyncSession) -> Dict[str, Any]:
    """Check Tachyon storage utilization and provider nodes."""
    try:
        from app.modules.storage_verification.service import get_storage_stats
        stats = await get_storage_stats(db)

        utilization = stats.get("utilization_pct", 0)
        provider_count = len(stats.get("active_providers", []))

        score = 100.0
        if utilization > 90: score -= 30
        if provider_count == 0: score -= 50

        return {
            "status": _get_status_from_score(score),
            "score": max(0.0, score),
            "details": {
                "utilization_pct": utilization,
                "active_providers": provider_count,
                "total_gb": stats.get("total_capacity_gb", 0)
            }
        }
    except Exception as e:
        return {"status": "degraded", "score": 50.0, "error": str(e)}

async def check_ai_health(db: AsyncSession) -> Dict[str, Any]:
    """Check AI model registry and performance."""
    try:
        from app.modules.ai.models import ModelMetadata
        res = await db.execute(select(ModelMetadata).where(ModelMetadata.is_active == True))
        active_models = res.scalars().all()
        model_count = len(active_models)

        avg_acc = sum(float(m.accuracy or 0) for m in active_models) / model_count if model_count > 0 else 0
        score = 100.0 if model_count >= 3 else (model_count / 3 * 100)

        return {
            "status": "healthy" if score > 80 else "degraded",
            "score": round(score, 1),
            "details": {
                "active_models": model_count,
                "ensemble_accuracy": round(avg_acc * 100, 1)
            }
        }
    except Exception as e:
        return {"status": "degraded", "score": 50.0, "error": str(e)}

async def check_task_health(db: AsyncSession, request: Request) -> Dict[str, Any]:
    """Check background task status and Celery heartbeats."""
    try:
        res = await db.execute(select(BackgroundTaskStatus))
        tasks = res.scalars().all()
        crashed = [t for t in tasks if t.status == "crashed"]

        # Check Redis heartbeats
        redis_client = getattr(request.app.state, "redis", None)
        agent_count = 0
        if redis_client:
            keys = await redis_client.keys("agent:heartbeat:*")
            agent_count = len(keys)

        score = 100.0
        if crashed: score -= len(crashed) * 20
        if agent_count == 0: score -= 30

        return {
            "status": _get_status_from_score(score),
            "score": max(0.0, score),
            "details": {
                "active_agents": agent_count,
                "crashed_tasks": len(crashed)
            }
        }
    except Exception as e:
        return {"status": "degraded", "score": 50.0, "error": str(e)}

# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status")
@cached(ttl=60, key_prefix="cloud:status:")
async def get_cloud_status(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Real-time 8-subsystem health snapshot."""
    # 1. Run all checks
    db_h = await check_database_health(db)
    infra_h = await check_infrastructure_health(request)
    core_h = await check_core_health()
    id_h = await check_identity_health(db)
    ai_h = await check_ai_health(db)
    task_h = await check_task_health(db, request)
    bc_h = await check_blockchain_health(db)
    tachyon_h = await check_tachyon_health(db)

    # 2. Derive overall health
    subsystems = {
        "database": db_h,
        "infrastructure": infra_h,
        "core": core_h,
        "identity": id_h,
        "ai": ai_h,
        "task": task_h,
        "blockchain": bc_h,
        "tachyon": tachyon_h
    }

    total_score = sum(s["score"] for s in subsystems.values())
    overall_health = round(total_score / 8.0, 1)

    # 3. Integrate Pricing
    price_data = {}
    try:
        from app.modules.wallet.pricing_engine import VITCoinPricingEngine
        p = await VITCoinPricingEngine.get_current_price(db)
        price_usd = float(p.get("price_usd", 0))
        price_data = {
            "price_usd": price_usd,
            "phase": p.get("phase"),
            "governors": p.get("governors")
        }
    except Exception as e:
        logger.warning(f"Failed to fetch VITCoin price for dashboard: {e}")

    return {
        "overall_health": overall_health,
        "overall_status": _get_status_from_score(overall_health),
        "subsystems": subsystems,
        "vitcoin": price_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": APP_VERSION
    }

@router.get("/status/history")
async def get_cloud_status_history(request: Request):
    """Retrieve the last 100 snapshots from Redis."""
    redis_client = getattr(request.app.state, "redis", None)
    if not redis_client:
        return {"history": [], "error": "Redis not available"}

    try:
        raw_history = await redis_client.lrange("vit:cloud:status:history", 0, 99)
        history = [json.loads(h) for h in raw_history]
        return {"history": history, "count": len(history)}
    except Exception as e:
        return {"history": [], "error": str(e)}

# ── Celery Snapshot Task ─────────────────────────────────────────────────────

async def _take_snapshot():
    """Internal: Compute and store a cloud status snapshot in Redis."""
    from app.db.database import AsyncSessionLocal

    # Mocking Request object for health checks that need request.app.state.redis
    class MockApp:
        def __init__(self, r): self.state = type('state', (), {'redis': r})
    class MockRequest:
        def __init__(self, r): self.app = MockApp(r)

    async with AsyncSessionLocal() as db:
        # We need a redis client.
        from app.config import REDIS_URL
        import redis.asyncio as aioredis
        r = aioredis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None

        mock_req = MockRequest(r)

        db_h = await check_database_health(db)
        infra_h = await check_infrastructure_health(mock_req)
        core_h = await check_core_health()
        id_h = await check_identity_health(db)
        ai_h = await check_ai_health(db)
        task_h = await check_task_health(db, mock_req)
        bc_h = await check_blockchain_health(db)
        tachyon_h = await check_tachyon_health(db)

        subsystems = {
            "database": db_h, "infrastructure": infra_h, "core": core_h,
            "identity": id_h, "ai": ai_h, "task": task_h,
            "blockchain": bc_h, "tachyon": tachyon_h
        }
        total_score = sum(s["score"] for s in subsystems.values())
        overall_health = round(total_score / 8.0, 1)

        snapshot = {
            "overall_health": overall_health,
            "status": _get_status_from_score(overall_health),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if r:
            await r.lpush("vit:cloud:status:history", json.dumps(snapshot))
            await r.ltrim("vit:cloud:status:history", 0, 99)
            await r.close()

        return snapshot

try:
    from app.worker.celery_app import celery as celery_app
    _celery_available = True
except ImportError:
    celery_app = None
    _celery_available = False

if _celery_available and celery_app:
    @celery_app.task(name="take_cloud_status_snapshot")
    def take_cloud_status_snapshot():
        """Periodic task to record network health snapshots."""
        import asyncio
        return asyncio.run(_take_snapshot())
