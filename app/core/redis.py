import logging
import os
import redis.asyncio as redis
from fakeredis import FakeAsyncRedis
from app.config import REDIS_URL, ENVIRONMENT

logger = logging.getLogger(__name__)

async def require_redis(app):
    if not REDIS_URL:
        if ENVIRONMENT == "production":
            logger.critical("REDIS_URL is not configured. Redis is required in production.")
            raise RuntimeError("REDIS_URL is not configured or unreachable. Redis is required in production.")
        else:
            logger.warning("REDIS_URL not found. Falling back to fakeredis (development).")
            app.state.redis = FakeAsyncRedis()
            return

    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        await client.ping()
        app.state.redis = client
        logger.info("Successfully connected to Redis.")
    except Exception as e:
        if ENVIRONMENT == "production":
            logger.critical(f"Failed to connect to Redis at {REDIS_URL}: {e}")
            raise RuntimeError("REDIS_URL is not configured or unreachable. Redis is required in production.")
        else:
            logger.warning(f"Redis connection failed: {e}. Falling back to fakeredis (development).")
            app.state.redis = FakeAsyncRedis()

async def close_redis(app):
    if hasattr(app.state, "redis"):
        await app.state.redis.close()
        logger.info("Redis connection closed.")
