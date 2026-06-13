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
