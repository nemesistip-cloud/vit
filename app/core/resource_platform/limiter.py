import logging
import time
from datetime import datetime, timedelta
from app.core.resource_platform.contract import IRateLimiter
from app.core.resource_platform.models import RateLimitInfo
from app.core.observability.manager import obs_manager

logger = logging.getLogger(__name__)

class RateLimiter(IRateLimiter):
    def __init__(self, redis_client):
        self.redis = redis_client
        self.prefix = "vit:limiter:"

    async def check_limit(self, key: str, limit: int, window_seconds: int) -> bool:
        full_key = f"{self.prefix}{key}"

        # Simple fixed window implementation
        current = await self.redis.get(full_key)
        if current is not None and int(current) >= limit:
            obs_manager.record_metric("resource_platform.rate_limit_exceeded", 1)
            return False

        # Atomic increment and expire
        pipeline = self.redis.pipeline()
        pipeline.incr(full_key)
        pipeline.expire(full_key, window_seconds)
        results = await pipeline.execute()

        obs_manager.record_metric("resource_platform.rate_limit_check", 1)
        return results[0] <= limit

    async def get_limit_info(self, key: str) -> RateLimitInfo:
        full_key = f"{self.prefix}{key}"
        current = await self.redis.get(full_key)
        ttl = await self.redis.ttl(full_key)

        return RateLimitInfo(
            key=key,
            limit=0, # Not stored in redis in this simple impl
            window_seconds=0,
            current_count=int(current or 0),
            reset_at=datetime.utcnow() + timedelta(seconds=max(0, ttl))
        )
