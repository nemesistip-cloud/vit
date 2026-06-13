"""app/worker/tasks/ml.py — Celery tasks for ML model operations."""
from __future__ import annotations

import asyncio
import logging

from app.worker.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="ml.trigger_training", max_retries=1, default_retry_delay=300)
def trigger_training(model_keys: list = None):
    """Trigger model re-training for the given keys (all 13 if None)."""
    async def _run():
        from app.db.database import AsyncSessionLocal
        from app.modules.training.service import trigger_training_job
        async with AsyncSessionLocal() as db:
            return await trigger_training_job(db, model_keys=model_keys)
    return asyncio.run(_run())


@celery.task(name="ml.evict_stale_models")
def evict_stale_models():
    """Evict models idle > MODEL_CACHE_TTL_SECONDS from the registry."""
    async def _run():
        from app.core.model_registry import registry
        return await registry.evict_stale()
    count = asyncio.run(_run())
    logger.info("Evicted %d stale model(s)", count)
    return {"evicted": count}
