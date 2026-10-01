import asyncio
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import AsyncMock

middleware_path = Path(__file__).parents[1] / "backend/app/api/middleware/logging.py"
middleware_spec = spec_from_file_location("vit_logging_middleware", middleware_path)
logging_middleware = module_from_spec(middleware_spec)
middleware_spec.loader.exec_module(logging_middleware)


def test_logging_middleware_records_requests_errors_and_latency(monkeypatch):
    redis_client = type("RedisStub", (), {"eval": AsyncMock(return_value=[2, 1, 1.5])})()
    monkeypatch.setattr(logging_middleware, "_get_redis_client", AsyncMock(return_value=redis_client))

    async def application(scope, receive, send):
        await send({"type": "http.response.start", "status": scope["test_status"], "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        return None

    middleware = logging_middleware.LoggingMiddleware(application)
    async def run_requests():
        for status in (200, 503):
            await middleware(
                {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/example",
                    "state": {},
                    "test_status": status,
                },
                receive,
                send,
            )

    asyncio.run(run_requests())

    assert redis_client.eval.await_count == 2
    for call, status in zip(redis_client.eval.await_args_list, (200, 503)):
        args = call.args
        assert args[1] == 6
        assert args[2:8] == (
            "metrics:window:24h",
            "metrics:requests:24h",
            "metrics:errors:24h",
            "metrics:response_total_ms:24h",
            "metrics:response_count:24h",
            "metrics:avg_response_ms",
        )
        assert args[8] == status
        assert args[9] >= 0
        assert args[10] == logging_middleware._METRICS_TTL_SECONDS


def test_logging_middleware_skips_health_and_metrics_requests(monkeypatch):
    redis_get = AsyncMock()
    monkeypatch.setattr(logging_middleware, "_get_redis_client", redis_get)

    async def application(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        return None

    middleware = logging_middleware.LoggingMiddleware(application)
    async def run_requests():
        for path in ("/ping", "/api/admin/system/metrics"):
            await middleware(
                {"type": "http", "method": "GET", "path": path, "state": {}},
                receive,
                send,
            )

    asyncio.run(run_requests())

    redis_get.assert_not_awaited()