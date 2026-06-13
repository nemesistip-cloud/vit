"""app/worker/tasks/tachyon.py — Celery tasks for Tachyon distributed storage."""
from __future__ import annotations

import asyncio
import logging

from app.worker.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="tachyon.health_check")
def tachyon_health_check():
    """Run Tachyon provider health checks."""
    async def _run():
        try:
            from tachyon.health import check_all_providers
            return await check_all_providers()
        except Exception as exc:
            logger.warning("Tachyon health check failed: %s", exc)
            return {"error": str(exc)}
    return asyncio.run(_run())
