"""app/core/redis.py — Redis client lifecycle with TLS + fakeredis fallback.

Supports both redis:// (plain) and rediss:// (TLS, e.g. Render managed Redis).
Falls back to fakeredis in non-production environments when REDIS_URL is absent
or unreachable. Raises RuntimeError in production so the deployment fails fast
rather than silently using ephemeral in-memory state.
"""
import logging
import os

import redis.asyncio as redis
from fakeredis import FakeAsyncRedis

from app.config import ENVIRONMENT, _clean_redis_url

logger = logging.getLogger(__name__)

# Global client for service-level access
redis_client = None


def _build_redis_client(redis_url: str):
    """Return a configured async Redis client for the given URL.

    For rediss:// (TLS) URLs — which Render managed Redis uses — we set
    ssl_cert_reqs="none" to skip certificate verification.  Render's Redis
    is signed by a private CA; without this flag the connection handshake
    raises ssl.SSLCertVerificationError and require_redis() fails hard in
    production.

    NOTE: the parameter is ssl_cert_reqs (with underscore between cert and reqs),
    NOT ssl_certreqs.  The latter is silently ignored by redis-py, leaving the
    default "required" in place and breaking TLS on Render.
    """
    common_kwargs: dict = {
        "decode_responses": True,
        "socket_connect_timeout": 5,
        "socket_timeout": 5,
    }
    if redis_url.startswith("rediss://"):
        # TLS — disable cert verification for Render managed Redis
        common_kwargs["ssl_cert_reqs"] = "none"
    return redis.from_url(redis_url, **common_kwargs)


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
            logger.warning(
                "Redis connection failed: %s. Falling back to fakeredis (development).", e
            )
            redis_client = FakeAsyncRedis()
            app.state.redis = redis_client


async def close_redis(app):
    if hasattr(app.state, "redis"):
        await app.state.redis.close()
        logger.info("Redis connection closed.")
