# app/api/middleware/rate_limit.py
# Value Intelligence Trust (VIT) — Rate Limiting Middleware
# G02: Redis sliding window (REDIS_URL) with in-memory deque fallback.
# SEC-07: idle buckets evicted after 2× the window to prevent unbounded growth.

from __future__ import annotations

import os
import time
import logging
from collections import defaultdict, deque
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.errors import error_response

log = logging.getLogger(__name__)

_EVICT_AFTER_SECONDS = 120


def _rate_limiting_enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "false"


def _extract_user_id(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            import base64, json as _json
            parts = token.split(".")
            if len(parts) == 3:
                payload_b64 = parts[1] + "=="
                payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
                uid = payload.get("sub") or payload.get("user_id") or payload.get("id")
                if uid:
                    return f"user:{uid}"
        except Exception:
            pass
    return None


# ── Redis backend (optional) ──────────────────────────────────────────────────

_redis_client = None
_redis_checked = False


def _get_redis():
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        return None
    try:
        import redis.asyncio as aioredis  # type: ignore
        _redis_client = aioredis.from_url(redis_url, decode_responses=True, socket_timeout=0.5)
        log.info("Rate limiter: Redis backend enabled (%s)", redis_url.split("@")[-1])
    except Exception as exc:
        log.warning("Rate limiter: Redis unavailable (%s) — using in-memory fallback", exc)
        _redis_client = None
    return _redis_client


async def _redis_sliding_window(redis, key: str, limit: int, window: int) -> tuple[bool, int, int]:
    """
    Lua-based atomic sliding window counter in Redis.
    Returns (allowed, remaining, retry_after_seconds).
    """
    now_ms = int(time.time() * 1000)
    window_ms = window * 1000
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
        result = await redis.eval(lua_script, 1, key, now_ms, window_ms, clear_before, limit)
        allowed = bool(result[0])
        remaining = int(result[1])
        retry_after = int(result[2])
        return allowed, remaining, retry_after
    except Exception as exc:
        log.warning("Redis sliding window error: %s — allowing request", exc)
        return True, limit, 0


# ── Middleware ────────────────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter keyed by (user_id > api_key > ip).

    Limits (per minute):
    - Anonymous (IP):        200 req/min general · 40 predict
    - API-key auth:         400 req/min general · 120 predict
    - JWT user:             600 req/min general · 200 predict

    Backend: Redis sliding window (REDIS_URL) with in-memory deque fallback.
    SEC-07: _buckets is cleaned up periodically.
    """

    ANON_LIMIT           = 200
    APIKEY_LIMIT         = 400
    JWT_LIMIT            = 600
    PREDICT_ANON_LIMIT   = 40
    PREDICT_APIKEY_LIMIT = 120
    PREDICT_JWT_LIMIT    = 200
    WINDOW_SECONDS       = 60
    EVICT_INTERVAL       = 300

    _BYPASS = (
        "/health", "/docs", "/openapi.json", "/redoc",
        "/static", "/favicon", "/ws", "/webhook",
        "/api/public", "/notifications/ws",
        "/config/public", "/config/public/refresh",
        "/analytics/summary", "/analytics/accuracy",
        "/analytics/leaderboard",
        "/matches/upcoming", "/matches/recent", "/matches/live",
        "/subscription/plans",
        "/api/wallet/vitcoin-price",
        "/ai-feed/recent",
        "/system/status",
    )

    def __init__(self, app):
        super().__init__(app)
        self._buckets: dict = defaultdict(deque)
        self._last_seen: dict = {}
        self._last_evict: float = time.time()

    def _evict_stale(self, now: float) -> None:
        if now - self._last_evict < self.EVICT_INTERVAL:
            return
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
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = int(self.WINDOW_SECONDS - (now - bucket[0])) + 1
            return False, 0, retry_after
        bucket.append(now)
        return True, max(0, limit - len(bucket)), 0

    async def dispatch(self, request: Request, call_next):
        if not _rate_limiting_enabled():
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(b) for b in self._BYPASS):
            return await call_next(request)

        api_key   = request.headers.get("x-api-key", "")
        ip        = request.client.host if request.client else "unknown"
        is_predict = "/predict" in path

        user_key = _extract_user_id(request)
        if user_key:
            key   = user_key
            limit = self.PREDICT_JWT_LIMIT if is_predict else self.JWT_LIMIT
        elif api_key:
            key   = f"key:{api_key}"
            limit = self.PREDICT_APIKEY_LIMIT if is_predict else self.APIKEY_LIMIT
        else:
            key   = f"ip:{ip}"
            limit = self.PREDICT_ANON_LIMIT if is_predict else self.ANON_LIMIT

        redis = _get_redis()
        now   = time.time()

        if redis is not None:
            redis_key = f"rl:{key}"
            allowed, remaining, retry_after = await _redis_sliding_window(
                redis, redis_key, limit, self.WINDOW_SECONDS
            )
        else:
            allowed, remaining, retry_after = self._in_memory_check(key, limit, now)

        if not allowed:
            return error_response(
                request=request,
                status_code=429,
                code="rate_limit_exceeded",
                message="Rate limit exceeded. Please slow down.",
                details={
                    "limit": limit,
                    "window_seconds": self.WINDOW_SECONDS,
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"]     = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
