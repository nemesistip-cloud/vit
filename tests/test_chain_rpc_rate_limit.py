import pytest

from app.api.middleware import rate_limit
from app.api.middleware.rate_limit import RateLimitMiddleware


async def _call_middleware(middleware, path="/api/chain/rpc"):
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [(b"x-forwarded-for", b"203.0.113.25")],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "root_path": "",
    }
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await middleware(scope, receive, send)
    return next(message["status"] for message in messages if message["type"] == "http.response.start")


@pytest.mark.asyncio
async def test_chain_rpc_uses_100_request_sliding_window(monkeypatch):
    monkeypatch.setattr(rate_limit, "_rate_limiting_enabled", lambda: True)
    monkeypatch.setattr(rate_limit, "_get_redis", lambda: None)
    monkeypatch.setattr(rate_limit, "ENVIRONMENT", "development")
    middleware = RateLimitMiddleware(lambda *_args: _send_ok(*_args))

    statuses = [await _call_middleware(middleware) for _ in range(101)]

    assert statuses[:100] == [200] * 100
    assert statuses[100] == 429


@pytest.mark.asyncio
async def test_chain_rpc_falls_back_to_in_memory_without_shared_redis_in_production(monkeypatch):
    monkeypatch.setattr(rate_limit, "_rate_limiting_enabled", lambda: False)
    monkeypatch.setattr(rate_limit, "_get_redis", lambda: None)
    monkeypatch.setattr(rate_limit, "ENVIRONMENT", "production")
    middleware = RateLimitMiddleware(lambda *_args: _send_ok(*_args))

    # Should fall back gracefully to in-memory rate limiting and return 200 rather than 503
    assert await _call_middleware(middleware) == 200


async def _send_ok(scope, _receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})
