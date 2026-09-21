"""
app/tasks/settlement_task.py
─────────────────────────────
Supervised settlement background worker.

Phase 1 hardening: asyncio task is now named, tracked, and supervised.
Restarts automatically on crash (up to _MAX_RESTARTS). Exposes stop handle
for clean shutdown. Migrate to Celery when the task queue is wired in.
"""
import asyncio
import logging
from typing import Optional
from app.db.database import get_db
from app.services.settlement_service import run_auto_settlement

logger = logging.getLogger(__name__)

_settlement_task: Optional[asyncio.Task] = None
_MAX_RESTARTS = 10
_RESTART_DELAY = 30
_CYCLE_INTERVAL = 900  # 15 minutes


async def settlement_worker() -> None:
    logger.info("[settlement] Worker started.")
    while True:
        try:
            async for db in get_db():
                result = await run_auto_settlement(db)
                settled = result.get("settled_matches", 0)
                if settled > 0:
                    logger.info("[settlement] %d matches settled, %d predictions updated.",
                                settled, result.get("predictions_updated", 0))
                break
        except asyncio.CancelledError:
            logger.info("[settlement] Worker cancelled — exiting.")
            raise
        except Exception as exc:
            logger.error("[settlement] Cycle error: %s", exc, exc_info=True)
        await asyncio.sleep(_CYCLE_INTERVAL)


async def _supervised() -> None:
    restarts = 0
    while restarts < _MAX_RESTARTS:
        try:
            await settlement_worker()
        except asyncio.CancelledError:
            logger.info("[settlement] Supervisor received cancellation — clean shutdown.")
            return
        except Exception as exc:
            restarts += 1
            logger.error("[settlement] Crash (restart %d/%d): %s", restarts, _MAX_RESTARTS, exc, exc_info=True)
            if restarts < _MAX_RESTARTS:
                await asyncio.sleep(_RESTART_DELAY)
    logger.critical("[settlement] Giving up after %d restarts — manual intervention required.", _MAX_RESTARTS)


def _on_done(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        logger.critical("[settlement] Task exited with exception: %s", exc, exc_info=True)


def start_settlement_worker() -> asyncio.Task:
    """Schedule the supervised worker. Returns Task for caller to track/cancel."""
    global _settlement_task
    if _settlement_task and not _settlement_task.done():
        logger.warning("[settlement] Already running — not starting duplicate.")
        return _settlement_task
    _settlement_task = asyncio.create_task(_supervised(), name="settlement-worker-supervised")
    _settlement_task.add_done_callback(_on_done)
    logger.info("[settlement] Supervised task scheduled.")
    return _settlement_task


def stop_settlement_worker() -> None:
    global _settlement_task
    if _settlement_task and not _settlement_task.done():
        _settlement_task.cancel()
        logger.info("[settlement] Cancellation requested.")
