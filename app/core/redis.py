"""app/core/redis.py — Redis client lifecycle with TLS + fakeredis fallback.

Supports both redis:// (plain) and rediss:// (TLS, e.g. Render managed Redis).
Falls back to fakeredis in non-production environments when REDIS_URL is absent
or unreachable. Raises RuntimeError in production so the deployment fails fast
rather than silently using ephemeral in-memory state.
"""
import logging
import os
import ssl

import redis.asyncio as redis
from fakeredis import FakeAsyncRedis

from app.config import ENVIRONMENT, _clean_redis_url

logger = logging.getLogger(__name__)

# Global client for service-level access
redis_client = None


def _build_redis_client(redis_url: str):
    """Return a configured async Redis client for the given URL.

    Automatically enables TLS for rediss:// URLs (Render managed Redis uses TLS).
    """
    if redis_url.startswith("rediss://"):
        # TLS connection — skip certificate verification for managed Redis
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        return redis.from_url(
            redis_url,
            decode_responses=True,
            ssl_certreqs=ssl.CERT_NONE,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )


async def require_redis(app):
    global redis_client
    # Read live from the environment: app.config's REDIS_URL constant is
    # frozen at import time (before ConfigurationManager.load() runs) and
    # can be stale/empty even when the real env var is set correctly.
    REDIS_URL = _clean_redis_url(os.getenv("REDIS_URL", ""))
    if not REDIS_URL:
        if ENVIRONMENT == "production":
            logger.critical("REDIS_URL is not configured. Redis is required in production.")
            raise RuntimeError("REDIS_URL is not configured or unreachable. Redis is required in production.")
        else:
            logger.warning("REDIS_URL not found. Falling back to fakeredis (development).")
            redis_client = FakeAsyncRedis()
            app.state.redis = redis_client
            return

    try:
        client = _build_redis_client(REDIS_URL)
        await client.ping()
        redis_client = client
        app.state.redis = client
        logger.info("Successfully connected to Redis at %s", REDIS_URL.split("@")[-1])
    except Exception as e:
        if ENVIRONMENT == "production":
            logger.critical("Failed to connect to Redis: %s", e)
            raise RuntimeError(f"Redis connection failed: {e}") from e
        else:
            logger.warning("Redis connection failed: %s. Falling back to fakeredis (development).", e)
            redis_client = FakeAsyncRedis()
            app.state.redis = redis_client


async def close_redis(app):
    if hasattr(app.state, "redis"):
        await app.state.redis.close()
        logger.info("Redis connection closed.")
