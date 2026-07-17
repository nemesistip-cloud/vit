import pytest
from unittest.mock import AsyncMock
from app.core.resource_platform.locks import DistributedLockManager

@pytest.mark.asyncio
async def test_lock_lifecycle():
    redis = AsyncMock()
    redis.set.return_value = True
    redis.eval.return_value = 1

    dlm = DistributedLockManager(redis)

    # Acquire
    success = await dlm.acquire("test-lock", "owner-1")
    assert success is True
    redis.set.assert_called_once()

    # Release
    success = await dlm.release("test-lock", "owner-1")
    assert success is True
    redis.eval.assert_called_once()
