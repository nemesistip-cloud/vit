"""app/core/redis.py — Centralized Redis client factory and lifecycle management.

Supports both redis:// (plain) and rediss:// (TLS, e.g. Render managed Redis).
Provides helper functions for both async (`build_redis_client`) and sync
(`build_sync_redis_client`) connections, automatically configuring SSL options
for TLS endpoints to avoid certificate verification failures on Render.
Falls back to fakeredis in non-production environments when REDIS_URL is absent
or unreachable. Raises RuntimeError in production so the deployment fails fast
rather than silently using ephemeral in-memory state.
"""
import logging
import os
from typing import Any, Optional

import redis.asyncio as redis
import redis as sync_redis
from fakeredis import FakeAsyncRedis

from app.config import ENVIRONMENT, _clean_redis_url

logger = logging.getLogger(__name__)

# Global client for service-level access
redis_client = None


def build_redis_client(redis_url: str = "", **kwargs) -> redis.Redis:
    """Return a configured async Redis client for the given URL.

    For rediss:// (TLS) URLs — which Render managed Redis uses — we set
    ssl_cert_reqs="none" to skip certificate verification unless specified otherwise.
    Render's Redis is signed by a private CA; without this flag the connection handshake
    raises ssl.SSLCertVerificationError and require_redis() fails hard in
    production.

    NOTE: the parameter is ssl_cert_reqs (with underscore between cert and
    reqs), NOT ssl_certreqs.  The latter is silently ignored by redis-py,
    leaving the default "required" in place and breaking TLS on Render.
    """
    url = _clean_redis_url(redis_url or os.getenv("REDIS_URL", ""))
    if not url:
        raise ValueError("REDIS_URL is empty or not provided.")

    options: dict[str, Any] = {
        "decode_responses": True,
        "socket_connect_timeout": 5,
        "socket_timeout": 5,
    }
    options.update(kwargs)

    if url.startswith("rediss://") and "ssl_cert_reqs" not in options:
        options["ssl_cert_reqs"] = "none"

    return redis.from_url(url, **options)


def build_sync_redis_client(redis_url: str = "", **kwargs) -> sync_redis.Redis:
    """Return a configured synchronous Redis client for the given URL."""
    url = _clean_redis_url(redis_url or os.getenv("REDIS_URL", ""))
    if not url:
        raise ValueError("REDIS_URL is empty or not provided.")

    options: dict[str, Any] = {
        "decode_responses": True,
        "socket_connect_timeout": 5,
        "socket_timeout": 5,
    }
    options.update(kwargs)

    if url.startswith("rediss://") and "ssl_cert_reqs" not in options:
        options["ssl_cert_reqs"] = "none"

    return sync_redis.from_url(url, **options)


# Backwards compatibility alias
_build_redis_client = build_redis_client


async def require_redis(app):
    global redis_client
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
        client = build_redis_client(REDIS_URL)
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
