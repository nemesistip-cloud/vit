"""app/api/middleware/rate_limit.py — Pure ASGI HTTP rate-limiting middleware."""

from __future__ import annotations

import asyncio
import time
import logging
from collections import defaultdict, deque
from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send
from app.core.errors import error_response

import os
from app.config import RATE_LIMIT_ENABLED, _clean_redis_url

log = logging.getLogger(__name__)

# In-memory buckets older than this (seconds) are evicted on the next sweep.
_EVICT_AFTER_SECONDS = 120

def _rate_limiting_enabled() -> bool:
    return RATE_LIMIT_ENABLED

def _extract_user_id(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    try:
        import base64, json as _json
        parts = token.split(".")
        if len(parts) != 3: return None
        payload_b64 = parts[1] + "=="
        payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
        uid = payload.get("sub") or payload.get("user_id") or payload.get("id")
        if uid: return f"user:{uid}"
    except Exception: pass
    return None

def _get_client_ip(request: Request) -> str:
    """Extract client IP, preferring X-Forwarded-For from proxies (e.g. Render)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # X-Forwarded-For: client, proxy1, proxy2
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# ── Redis state ───────────────────────────────────────────────────────────────

_redis_client = None
_redis_checked = False
_redis_disabled = False        # Circuit breaker: set True after first async failure
_redis_fail_count = 0
_REDIS_FAIL_THRESHOLD = 3      # Disable Redis after this many consecutive failures

def _get_redis():
    """Return a cached async Redis client, or None if unavailable / circuit-broken."""
    global _redis_client, _redis_checked
    if _redis_checked: return _redis_client
    _redis_checked = True
    # Read live from the environment: app.config's REDIS_URL constant is
    # frozen at import time (before ConfigurationManager.load() runs) and
    # can be stale/empty even when the real env var is set correctly.
    redis_url = _clean_redis_url(os.getenv("REDIS_URL", ""))
    if not redis_url: return None
    try:
        import redis.asyncio as aioredis
        # socket_connect_timeout caps the initial TCP connect; socket_timeout caps
        # individual operations. Both must be short so a broken Redis URL does not
        # add per-request latency.
        _redis_client = aioredis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
        log.info("Rate limiter: Redis backend enabled")
    except Exception as exc:
        log.warning("Rate limiter: Redis unavailable (%s) — using in-memory fallback", exc)
        _redis_client = None
    return _redis_client


def _mark_redis_failure():
    """Increment failure counter; disable Redis circuit if threshold exceeded."""
    global _redis_disabled, _redis_fail_count, _redis_client
    _redis_fail_count += 1
    if _redis_fail_count >= _REDIS_FAIL_THRESHOLD:
        if not _redis_disabled:
            log.warning(
                "Rate limiter: Redis failed %d times consecutively — "
                "switching to in-memory fallback for this process lifetime. "
                "Fix REDIS_URL and redeploy to re-enable.",
                _REDIS_FAIL_THRESHOLD,
            )
            _redis_disabled = True
            _redis_client = None   # Force _get_redis() to return None hereafter


def _reset_redis_failure():
    global _redis_fail_count
    _redis_fail_count = 0


async def _redis_sliding_window(redis, key: str, limit: int, window: int) -> tuple[bool, int, int]:
    """Lua-atomic sliding-window rate check. Falls back gracefully on any error."""
    global _redis_disabled
    if _redis_disabled:
        return True, limit, 0

    now_ms       = int(time.time() * 1000)
    window_ms    = window * 1000
    clear_before = now_ms - window_ms
    lua_script = """
local key         = KEYS[1]
local now         = tonumber(ARGV[1])
local window_ms   = tonumber(ARGV[2])
local clear_before = tonumber(ARGV[3])
local limit       = tonumber(ARGV[4])
redis.call('ZREMRANGEBYSCORE', key, '-inf', clear_before)
local count = redis.call('ZCARD', key)
if count < limit then
    redis.call('ZADD', key, now, now .. '-' .. math.random(1e9))
    redis.call('PEXPIRE', key, window_ms * 2)
    return {1, limit - count - 1, 0}
else
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry  = math.ceil((tonumber(oldest[2]) + window_ms - now) / 1000) + 1
    return {0, 0, retry}
end
"""
    try:
        result = await asyncio.wait_for(
            redis.eval(lua_script, 1, key, now_ms, window_ms, clear_before, limit),
            timeout=0.5,
        )
        _reset_redis_failure()
        return bool(result[0]), int(result[1]), int(result[2])
    except Exception as exc:
        log.warning("Redis sliding window error: %s — allowing request", exc)
        _mark_redis_failure()
        return True, limit, 0

class RateLimitMiddleware:
    ANON_LIMIT           = 60
    APIKEY_LIMIT         = 180
    JWT_LIMIT            = 300
    PREDICT_ANON_LIMIT   = 20
    PREDICT_APIKEY_LIMIT = 80
    PREDICT_JWT_LIMIT    = 120
    WINDOW_SECONDS = 60
    EVICT_INTERVAL = 300
    _BYPASS_PREFIXES = (
        "/ping", "/health", "/docs", "/openapi.json", "/redoc", "/static", "/favicon",
        "/ws", "/webhook", "/api/public", "/notifications/ws", "/assets", "/scripts",
    )
    _BYPASS_EXTENSIONS = (
        ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".json", ".map",
    )

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._buckets: dict = defaultdict(deque)
        self._last_seen: dict = {}
        self._last_evict: float = time.time()

    def _evict_stale(self, now: float) -> None:
        if now - self._last_evict < self.EVICT_INTERVAL: return
        self._last_evict = now
        cutoff = now - _EVICT_AFTER_SECONDS
        stale = [k for k, ts in self._last_seen.items() if ts < cutoff]
        for k in stale:
            self._buckets.pop(k, None)
            self._last_seen.pop(k, None)

    def _in_memory_check(self, key: str, limit: int, now: float) -> tuple[bool, int, int]:
        self._last_seen[key] = now
        self._evict_stale(now)
        window_start = now - self.WINDOW_SECONDS
        bucket = self._buckets[key]
        while bucket and bucket[0] < window_start: bucket.popleft()
        if len(bucket) >= limit:
            retry_after = int(self.WINDOW_SECONDS - (now - bucket[0])) + 1
            return False, 0, retry_after
        bucket.append(now)
        return True, max(0, limit - len(bucket)), 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or not _rate_limiting_enabled():
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path

        # Enhanced bypass: prefix check + extension check
        if any(path.startswith(b) for b in self._BYPASS_PREFIXES) or any(path.endswith(e) for e in self._BYPASS_EXTENSIONS):
            await self.app(scope, receive, send)
            return

        api_key    = request.headers.get("x-api-key", "")
        ip         = _get_client_ip(request)
        is_predict = "/predict" in path
        user_key = _extract_user_id(request)

        if user_key:
            key, limit = user_key, (self.PREDICT_JWT_LIMIT if is_predict else self.JWT_LIMIT)
        elif api_key:
            key, limit = f"key:{api_key}", (self.PREDICT_APIKEY_LIMIT if is_predict else self.APIKEY_LIMIT)
        else:
            key, limit = f"ip:{ip}", (self.PREDICT_ANON_LIMIT if is_predict else self.ANON_LIMIT)

        redis = _get_redis()
        now   = time.time()
        if redis:
            allowed, remaining, retry_after = await _redis_sliding_window(redis, f"rl:{key}", limit, self.WINDOW_SECONDS)
        else:
            allowed, remaining, retry_after = self._in_memory_check(key, limit, now)

        if not allowed:
            res = error_response(
                request=request, status_code=429, code="rate_limit_exceeded",
                message="Rate limit exceeded. Please slow down.",
                details={"limit": limit, "window_seconds": self.WINDOW_SECONDS, "retry_after": retry_after},
                headers={"Retry-After": str(retry_after)},
            )
            await res(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-ratelimit-limit", str(limit).encode()))
                headers.append((b"x-ratelimit-remaining", str(remaining).encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
