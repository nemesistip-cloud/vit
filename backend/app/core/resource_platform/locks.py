import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from app.core.resource_platform.contract import IDistributedLockManager
from app.core.observability.manager import obs_manager

logger = logging.getLogger(__name__)

class DistributedLockManager(IDistributedLockManager):
    def __init__(self, redis_client):
        self.redis = redis_client
        self.prefix = "vit:lock:"

    async def acquire(self, lock_id: str, owner: str, ttl_seconds: int = 60) -> bool:
        key = f"{self.prefix}{lock_id}"
        # NX: Set if not exists, PX: expiry in milliseconds
        success = await self.redis.set(key, owner, nx=True, px=ttl_seconds * 1000)

        if success:
            obs_manager.record_metric("resource_platform.lock_acquired", 1)
            return True
        return False

    async def release(self, lock_id: str, owner: str) -> bool:
        key = f"{self.prefix}{lock_id}"
        # Use Lua script for atomic check-and-delete
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await self.redis.eval(script, 1, key, owner)
        if result:
            obs_manager.record_metric("resource_platform.lock_released", 1)
            return True
        return False

    async def extend(self, lock_id: str, owner: str, ttl_seconds: int = 60) -> bool:
        key = f"{self.prefix}{lock_id}"
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("pexpire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        result = await self.redis.eval(script, 1, key, owner, ttl_seconds * 1000)
        return bool(result)
