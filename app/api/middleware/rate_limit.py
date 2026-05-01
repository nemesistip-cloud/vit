# app/api/middleware/rate_limit.py
# VIT Sports Intelligence — Rate Limiting Middleware
# In-memory sliding window rate limiter (per IP + per API key)
# SEC-07: idle buckets are evicted after 2× the window to prevent unbounded growth.

import os
import time
from collections import defaultdict, deque
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.errors import error_response

_EVICT_AFTER_SECONDS = 120  # evict buckets idle for 2× the window


def _rate_limiting_enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "false"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter.
    - Anonymous: 30 req/min per IP
    - Authenticated: 120 req/min per API key
    - Prediction endpoint stricter: 20/min anon, 60/min auth

    SEC-07: _buckets is cleaned up periodically — idle keys are evicted after
    2 minutes so memory usage stays bounded even under rotating-IP bot traffic.
    """

    ANON_LIMIT = 30
    AUTH_LIMIT = 120
    PREDICT_ANON_LIMIT = 20
    PREDICT_AUTH_LIMIT = 60
    WINDOW_SECONDS = 60
    EVICT_INTERVAL = 300  # run eviction pass every 5 minutes

    # Routes that bypass rate limiting completely
    _BYPASS = ("/health", "/docs", "/openapi.json", "/redoc", "/static")

    def __init__(self, app):
        super().__init__(app)
        self._buckets: dict = defaultdict(deque)
        self._last_seen: dict = {}      # key → last request timestamp
        self._last_evict: float = time.time()

    def _evict_stale(self, now: float) -> None:
        """Remove buckets that haven't seen traffic in _EVICT_AFTER_SECONDS."""
        if now - self._last_evict < self.EVICT_INTERVAL:
            return
        self._last_evict = now
        cutoff = now - _EVICT_AFTER_SECONDS
        stale = [k for k, ts in self._last_seen.items() if ts < cutoff]
        for k in stale:
            self._buckets.pop(k, None)
            self._last_seen.pop(k, None)

    async def dispatch(self, request: Request, call_next):
        if not _rate_limiting_enabled():
            return await call_next(request)

        path = request.url.path

        if any(path.startswith(b) for b in self._BYPASS):
            return await call_next(request)

        api_key = request.headers.get("x-api-key", "")
        ip = request.client.host if request.client else "unknown"
        key = f"key:{api_key}" if api_key else f"ip:{ip}"
        is_predict = "/predict" in path

        if api_key:
            limit = self.PREDICT_AUTH_LIMIT if is_predict else self.AUTH_LIMIT
        else:
            limit = self.PREDICT_ANON_LIMIT if is_predict else self.ANON_LIMIT

        now = time.time()
        self._last_seen[key] = now
        self._evict_stale(now)

        window_start = now - self.WINDOW_SECONDS
        bucket = self._buckets[key]

        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= limit:
            retry_after = int(self.WINDOW_SECONDS - (now - bucket[0])) + 1
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

        bucket.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - len(bucket)))
        return response
