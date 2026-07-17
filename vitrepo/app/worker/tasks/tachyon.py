"""app/worker/tasks/tachyon.py — Tachyon swarm health & GC tasks."""
from __future__ import annotations
import asyncio, json, logging, os, time
from celery.utils.log import get_task_logger
from app.worker.celery_app import celery

logger = get_task_logger(__name__)


@celery.task(name="tachyon.health_check", max_retries=2, default_retry_delay=120)
def health_check():
    """Ping all Tachyon storage providers and cache result in Redis."""
    return asyncio.run(_run_health())


async def _run_health():
    result = {"ts": time.time(), "nodes": {}, "healthy": 0, "degraded": 0}
    try:
        from app.services.tachyon_client import tachyon_client
        status = await tachyon_client.health()
        result["nodes"]   = status.get("nodes", {})
        result["healthy"] = sum(1 for v in result["nodes"].values() if v.get("ok"))
        result["degraded"]= len(result["nodes"]) - result["healthy"]
    except ImportError:
        result["error"] = "tachyon_client not available"
    except Exception as exc:
        result["error"] = str(exc)
        logger.warning("[tachyon.health] %s", exc)

    try:
        import redis as _r
        r = _r.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
        r.setex("tachyon:health:last", 7200, json.dumps(result))
        r.close()
    except Exception: pass
    logger.info("[tachyon.health] healthy=%d degraded=%d",
                result["healthy"], result["degraded"])
    return result


@celery.task(name="tachyon.gc_orphans", max_retries=1, default_retry_delay=600,
             soft_time_limit=600, time_limit=720)
def gc_orphans():
    """Remove orphaned blobs from Tachyon nodes."""
    return asyncio.run(_run_gc())


async def _run_gc():
    result = {"ts": time.time(), "freed_bytes": 0, "orphans_removed": 0}
    try:
        from app.services.tachyon_client import tachyon_client
        result.update(await tachyon_client.gc())
    except ImportError:
        result["error"] = "tachyon_client not available"
    except Exception as exc:
        result["error"] = str(exc)
        logger.warning("[tachyon.gc] %s", exc)
    logger.info("[tachyon.gc] freed=%.1fKB removed=%d",
                result["freed_bytes"] / 1024, result["orphans_removed"])
    return result
