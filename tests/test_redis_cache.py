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


def test_build_redis_client_tls():
    """Test that build_redis_client and build_sync_redis_client add ssl_cert_reqs='none' for rediss:// URLs."""
    from app.core.redis import build_redis_client, build_sync_redis_client

    async_client = build_redis_client("rediss://:password@localhost:6379/0")
    conn_kwargs = async_client.connection_pool.connection_kwargs
    assert conn_kwargs.get("ssl_cert_reqs") == "none"

    sync_client = build_sync_redis_client("rediss://:password@localhost:6379/0")
    sync_conn_kwargs = sync_client.connection_pool.connection_kwargs
    assert sync_conn_kwargs.get("ssl_cert_reqs") == "none"


@pytest.mark.asyncio
async def test_require_redis_fallback():
    """Test that require_redis falls back to FakeAsyncRedis when REDIS_URL is not provided in dev."""
    from app.core.redis import require_redis, FakeAsyncRedis

    class DummyApp:
        def __init__(self):
            self.state = type("state", (), {})()

    app = DummyApp()
    with patch("os.getenv", return_value=""):
        await require_redis(app)
        assert isinstance(app.state.redis, FakeAsyncRedis)
