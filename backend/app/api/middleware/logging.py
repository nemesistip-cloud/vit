import time
import logging
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("app.access")
_METRICS_TTL_SECONDS = 24 * 60 * 60
_METRICS_EXCLUDED_PATHS = {
    "/ping",
    "/health",
    "/ready",
    "/readiness",
    "/api/admin/system/metrics",
}
_RECORD_REQUEST_METRICS = """
local ttl = redis.call('TTL', KEYS[1])
if ttl < 0 then
    ttl = tonumber(ARGV[3])
    redis.call('SET', KEYS[1], '1', 'EX', ttl)
end

local requests = redis.call('INCR', KEYS[2])
if redis.call('TTL', KEYS[2]) < 0 then redis.call('EXPIRE', KEYS[2], ttl) end

local errors = tonumber(redis.call('GET', KEYS[3]) or '0')
if tonumber(ARGV[1]) >= 500 then
    errors = redis.call('INCR', KEYS[3])
    if redis.call('TTL', KEYS[3]) < 0 then redis.call('EXPIRE', KEYS[3], ttl) end
end

local total = redis.call('INCRBYFLOAT', KEYS[4], tonumber(ARGV[2]))
if redis.call('TTL', KEYS[4]) < 0 then redis.call('EXPIRE', KEYS[4], ttl) end
local count = redis.call('INCR', KEYS[5])
if redis.call('TTL', KEYS[5]) < 0 then redis.call('EXPIRE', KEYS[5], ttl) end

local average = tonumber(total) / count
redis.call('SET', KEYS[6], tostring(average), 'EX', ttl)
return {requests, errors, average}
"""


async def _get_redis_client():
    from app.core.redis import get_redis

    return await get_redis()


class LoggingMiddleware:
    """Pure ASGI request/response logging middleware."""
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "UNKNOWN")
        status_code = 500

        # We'll log the completion in a send wrapper
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status = message["status"]
                status_code = status
                process_time = time.perf_counter() - start_time

                # Fetch request_id from scope state if set by add_request_id middleware
                state = scope.get("state", {})
                request_id = state.get("request_id", "unknown")

                # Inject timing header
                headers = list(message.get("headers", []))
                headers.append((b"x-process-time", str(process_time).encode()))
                message["headers"] = headers

                logger.info(
                    "request_completed request_id=%s status=%s duration_seconds=%.3f",
                    request_id,
                    status,
                    process_time,
                )
            await send(message)

        # Log start (request_id might not be available yet if add_request_id hasn't run,
        # but in main.py order, add_request_id is outer)
        request_id = scope.get("state", {}).get("request_id", "unknown")
        logger.info(
            "request_started request_id=%s method=%s path=%s",
            request_id,
            method,
            path,
        )

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            # Re-log failure if not caught by exception handlers
            process_time = time.perf_counter() - start_time
            request_id = scope.get("state", {}).get("request_id", "unknown")
            logger.error(
                "request_failed request_id=%s method=%s path=%s duration_seconds=%.3f",
                request_id,
                method,
                path,
                process_time,
            )
            raise
        finally:
            if path not in _METRICS_EXCLUDED_PATHS:
                try:
                    redis_client = await _get_redis_client()
                    if redis_client is not None:
                        await redis_client.eval(
                            _RECORD_REQUEST_METRICS,
                            6,
                            "metrics:window:24h",
                            "metrics:requests:24h",
                            "metrics:errors:24h",
                            "metrics:response_total_ms:24h",
                            "metrics:response_count:24h",
                            "metrics:avg_response_ms",
                            status_code,
                            round((time.perf_counter() - start_time) * 1000, 3),
                            _METRICS_TTL_SECONDS,
                        )
                except Exception as exc:
                    logger.debug("request_metrics_write_failed error=%s", type(exc).__name__)
