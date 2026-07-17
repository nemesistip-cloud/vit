"""app/worker/dlq.py — Dead-Letter Queue handler.

Terminal task failures (max_retries exceeded) are written to Redis list
  worker:dlq  (LPUSH, newest first, capped at 500 entries)

Admin endpoint:  GET /api/agents/dlq
Admin endpoint:  DELETE /api/agents/dlq  (purge)
"""
from __future__ import annotations

import json, logging, os, time
from typing import Any, Dict, List

from celery import signals

logger = logging.getLogger(__name__)
_DLQ_KEY = "worker:dlq"
_DLQ_MAX = 500


def _r():
    import redis
    return redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
                          socket_connect_timeout=3)


@signals.task_failure.connect
def on_task_failure(sender, task_id, exception, args, kwargs, einfo, **__):
    """Write every terminal failure into the Redis DLQ."""
    entry = {
        "task_id":   task_id,
        "task_name": getattr(sender, "name", str(sender)),
        "args":      str(args)[:200],
        "kwargs":    str(kwargs)[:200],
        "error":     repr(exception)[:500],
        "ts":        time.time(),
    }
    try:
        rc = _r()
        pipe = rc.pipeline()
        pipe.lpush(_DLQ_KEY, json.dumps(entry))
        pipe.ltrim(_DLQ_KEY, 0, _DLQ_MAX - 1)
        pipe.execute()
        rc.close()
        logger.error("[dlq] queued %s → %s", entry["task_name"], repr(exception)[:80])
    except Exception as exc:
        logger.warning("[dlq] Redis write failed: %s", exc)


def read_dlq(limit: int = 50) -> List[Dict[str, Any]]:
    try:
        rc = _r(); raw = rc.lrange(_DLQ_KEY, 0, limit - 1); rc.close()
        return [json.loads(e) for e in raw]
    except Exception as exc:
        logger.warning("[dlq] read failed: %s", exc); return []


def purge_dlq() -> int:
    try:
        rc = _r(); n = rc.llen(_DLQ_KEY); rc.delete(_DLQ_KEY); rc.close(); return n
    except Exception: return 0
