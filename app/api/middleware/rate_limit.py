# app/api/middleware/rate_limit.py
# VIT Sports Intelligence — Rate Limiting Middleware
# In-memory sliding window rate limiter (per IP + per API key)

import os
import time
from collections import defaultdict, deque
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.errors import error_response


def _rate_limiting_enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "false"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter.
    - Anonymous: 30 req/min per IP
    - Authenticated: 120 req/min per API key
    - Prediction endpoint stricter: 20/min anon, 60/min auth
    """

    ANON_LIMIT = 30
    AUTH_LIMIT = 120
    PREDICT_ANON_LIMIT = 20
    PREDICT_AUTH_LIMIT = 60
    WINDOW_SECONDS = 60

    _buckets: dict = defaultdict(deque)

    # Routes that bypass rate limiting completely
    _BYPASS = ("/health", "/docs", "/openapi.json", "/redoc", "/static")

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
