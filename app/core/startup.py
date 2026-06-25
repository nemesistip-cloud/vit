"""app/core/startup.py — Centralised async startup / shutdown sequences.

startup_sequence():
  1. Validate required secrets (WARN, never crash)
  2. Test DB connectivity   (WARN on failure)
  3. Test Redis connectivity (WARN on failure)
  4. Initialise ModelRegistry (empty — zero models loaded here)
  5. Print memory / config banner

shutdown_sequence():
  1. Evict all cached models from registry
  2. Close DB engine
  3. Close Redis connection
  4. Log clean shutdown

Note: Agents are intentionally NOT started here.
They run in the vit-worker Celery service (scripts/start_worker.sh).
"""

from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)

_REQUIRED = ["JWT_SECRET_KEY", "DATABASE_URL"]
_OPTIONAL = [
    "REDIS_URL", "PAYSTACK_SECRET_KEY",
    "FOOTBALL_DATA_API_KEY", "ODDS_API_KEY", "RESEND_API_KEY",
    "TELEGRAM_BOT_TOKEN", "ORACLE_API_KEY",
    "GDRIVE_SERVICE_ACCOUNT_JSON", "PI_APP_ID",
]


async def startup_sequence() -> None:
    """Run all pre-boot checks. Never raises."""
    t0 = time.monotonic()
    logger.info("[startup] beginning startup sequence")
    _validate_secrets()
    await _check_db()
    await _check_redis()
    _init_model_registry()
    _print_memory_banner()
    elapsed = round(time.monotonic() - t0, 2)
    logger.info("[startup] complete in %.2fs", elapsed)
    print(f"\u26a1 Startup checks done in {elapsed}s — models load on first request")


async def shutdown_sequence() -> None:
    """Graceful shutdown."""
    logger.info("[shutdown] beginning shutdown sequence")

    try:
        from app.core.model_registry import registry
        for name in list(registry._cache.keys()):
            await registry.unload(name)
        logger.info("[shutdown] model registry cleared")
    except Exception as exc:
        logger.warning("[shutdown] model eviction error: %s", exc)

    try:
        from app.db.database import engine
        await engine.dispose()
        logger.info("[shutdown] database engine disposed")
    except Exception as exc:
        logger.warning("[shutdown] db dispose error: %s", exc)

    try:
        redis_url = os.environ.get("REDIS_URL", "")
        if redis_url:
            import redis.asyncio as aioredis
            r = aioredis.from_url(redis_url)
            await r.aclose()
            logger.info("[shutdown] redis connection closed")
    except Exception as exc:
        logger.warning("[shutdown] redis close error: %s", exc)

    logger.info("[shutdown] clean shutdown complete")
    print("\U0001f6d1 VIT Network shutdown complete")


# ── Private ───────────────────────────────────────────────────────────────────

def _validate_secrets() -> None:
    missing_req = [k for k in _REQUIRED if not os.environ.get(k)]
    missing_opt = [k for k in _OPTIONAL if not os.environ.get(k)]
    if missing_req:
        for k in missing_req:
            logger.warning("[startup] MISSING REQUIRED SECRET: %s", k)
        print(f"\u26a0\ufe0f  Missing required: {', '.join(missing_req)}")
    else:
        print(f"\u2705 Required secrets: all {len(_REQUIRED)} present")
    if missing_opt:
        print(f"\u26a0\ufe0f  Optional missing (features disabled): {', '.join(missing_opt)}")


async def _check_db() -> None:
    try:
        from app.db.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("\u2705 Database: connection OK")
    except Exception as exc:
        logger.warning("[startup] database check failed: %s", exc)
        print(f"\u26a0\ufe0f  Database: {exc}")


async def _check_redis() -> None:
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        print("\u26a0\ufe0f  Redis: REDIS_URL not set — in-memory rate limiting only")
        return
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(redis_url, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        print("\u2705 Redis: connection OK")
    except Exception as exc:
        logger.warning("[startup] redis check failed: %s", exc)
        print(f"\u26a0\ufe0f  Redis: {exc} — in-memory fallback")


def _init_model_registry() -> None:
    try:
        from app.core.model_registry import registry  # noqa: F401
        print("\u2705 Model registry: initialised (0 models — lazy mode active)")
    except Exception as exc:
        logger.warning("[startup] model registry init error: %s", exc)


def _print_memory_banner() -> None:
    try:
        import psutil, os as _os
        rss_mb = psutil.Process(_os.getpid()).memory_info().rss / (1024 * 1024)
        limit = int(os.environ.get("MAX_PROCESS_RAM_MB", "400"))
        pct = round((rss_mb / limit) * 100, 1)
        status = "\u2705" if rss_mb < 200 else "\u26a0\ufe0f"
        print(f"\U0001f4ca Boot RAM: {rss_mb:.1f}MB / {limit}MB budget ({pct}%) {status}")
        if rss_mb > 200:
            logger.warning("[startup] boot RAM %.1fMB exceeds 200MB target", rss_mb)
    except Exception:
        pass
