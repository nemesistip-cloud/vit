import logging
import json
from typing import Any, Optional, Dict, Union
from datetime import timedelta

logger = logging.getLogger(__name__)

class CacheManager:
    """Standardized caching layer for the Persistence Platform."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache."""
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"[persistence] Cache read error for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[Union[int, timedelta]] = None):
        """Set a value in cache with optional TTL."""
        try:
            serialized = json.dumps(value)
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            await self.redis.set(key, serialized, ex=ttl)
        except Exception as e:
            logger.error(f"[persistence] Cache write error for {key}: {e}")

    async def delete(self, key: str):
        """Remove a value from cache."""
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"[persistence] Cache delete error for {key}: {e}")

    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching a pattern."""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"[persistence] Cache pattern invalidation error for {pattern}: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """Return cache performance metrics."""
        # This would integrate with observability
        return {
            "connected": self.redis is not None,
            "type": str(type(self.redis))
        }
