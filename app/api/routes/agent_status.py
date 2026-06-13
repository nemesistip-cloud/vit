"""app/api/routes/agent_status.py — Agent heartbeat status via Redis.

Reads heartbeat keys written by Celery worker agents.
Key pattern: agent:heartbeat:{name}  TTL 120s

GET /api/agents/status
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(tags=["Agents"])


@router.get("/api/agents/status")
async def agent_status() -> Dict[str, Any]:
    """Liveness snapshot of all autonomous agents via Redis heartbeats."""
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        return _in_process_fallback()
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(redis_url, socket_connect_timeout=2)
        keys = await r.keys("agent:heartbeat:*")
        agents: Dict[str, Any] = {}
        for raw_key in keys:
            key = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
            name = key.replace("agent:heartbeat:", "")
            raw_val = await r.get(key)
            if raw_val:
                try:
                    data = json.loads(raw_val.decode() if isinstance(raw_val, bytes) else raw_val)
                    data["stale"] = (time.time() - data.get("ts", 0)) > 120
                    agents[name] = data
                except Exception:
                    agents[name] = {"raw": str(raw_val), "stale": True}
        await r.aclose()
        return {"mode": "celery-worker", "redis": True,
                "agent_count": len(agents), "agents": agents, "ts": time.time()}
    except Exception as exc:
        return {"mode": "celery-worker", "redis": False,
                "error": str(exc), "agents": {}, "ts": time.time()}


def _in_process_fallback() -> Dict[str, Any]:
    try:
        from app.core.swarm_orchestrator import get_swarm
        snap = get_swarm().status()
        return {"mode": "in-process", "redis": False, **snap, "ts": time.time()}
    except Exception:
        return {"mode": "unknown", "redis": False, "agents": {}, "ts": time.time()}


@router.get("/api/agents/dlq")
async def get_dlq(limit: int = 50) -> dict:
    """Read the Dead-Letter Queue — tasks that exhausted all retries."""
    try:
        from app.worker.dlq import read_dlq
        entries = read_dlq(limit=min(limit, 200))
    except Exception as exc:
        entries = []
    return {"count": len(entries), "entries": entries, "ts": time.time()}


@router.delete("/api/agents/dlq")
async def purge_dlq_endpoint() -> dict:
    """Purge all entries from the Dead-Letter Queue."""
    try:
        from app.worker.dlq import purge_dlq
        removed = purge_dlq()
    except Exception:
        removed = 0
    return {"purged": removed, "ts": time.time()}


@router.get("/api/agents/retrain/status")
async def get_retrain_status() -> dict:
    """Last ML retrain run status from Redis."""
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        return {"status": "no_redis"}
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(redis_url, socket_connect_timeout=2)
        raw = await r.get("ml:retrain:status")
        acc_raw = await r.get("ml:accuracy:overall")
        acc_7d  = await r.get("ml:accuracy:7d")
        await r.aclose()
        import json as _j
        return {
            "retrain": _j.loads(raw) if raw else None,
            "accuracy_overall": _j.loads(acc_raw) if acc_raw else None,
            "accuracy_7d": _j.loads(acc_7d) if acc_7d else None,
            "ts": time.time(),
        }
    except Exception as exc:
        return {"error": str(exc), "ts": time.time()}
