import pytest
import json
from unittest.mock import AsyncMock, patch
from app.services.cache import cache

@pytest.mark.asyncio
async def test_cache_get_set():
    """Test that cache can set and get values with Redis mock."""
    with patch("app.services.cache._get_redis") as mock_get_redis:
        mock_r = AsyncMock()
        mock_get_redis.return_value = mock_r

        mock_r.get.return_value = json.dumps("value123")
        mock_r.set.return_value = True

        # Test GET
        val = await cache.get("test_key")
        assert val == "value123"
        mock_r.get.assert_called_with("test_key")

        # Test SET
        await cache.set("test_key", "value456", ttl=10)
        mock_r.set.assert_called_with("test_key", json.dumps("value456"), ex=10)

@pytest.mark.asyncio
async def test_cache_error_fallback():
    """Test that cache falls back to memory on Redis error."""
    with patch("app.services.cache._get_redis") as mock_get_redis:
        mock_r = AsyncMock()
        mock_get_redis.return_value = mock_r

        # Redis fails
        mock_r.get.side_effect = Exception("Redis Down")

        # Should NOT raise, but return from memory (which is empty)
        val = await cache.get("any_key")
        assert val is None

@pytest.mark.asyncio
async def test_cache_delete():
    """Test cache deletion."""
    with patch("app.services.cache._get_redis") as mock_get_redis:
        mock_r = AsyncMock()
        mock_get_redis.return_value = mock_r

        await cache.delete("test_key")
        mock_r.delete.assert_called_with("test_key")
