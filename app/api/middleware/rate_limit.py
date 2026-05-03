# app/api/middleware/rate_limit.py
# VIT Sports Intelligence — Rate Limiting Middleware
# In-memory sliding window rate limiter (per user JWT > per API key > per IP)
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


def _extract_user_id(request: Request) -> str | None:
    """Try to extract a stable user identifier from the JWT without full validation."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            # Decode payload without verifying (rate limiting only — not a security check)
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


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter keyed by (user_id > api_key > ip).

    Limits (per minute):
    - Anonymous (IP):        60 req/min general · 20 predict
    - API-key auth:         180 req/min general · 80 predict
    - JWT user:             300 req/min general · 120 predict

    SEC-07: _buckets is cleaned up periodically — idle keys are evicted after
    2 minutes so memory usage stays bounded even under rotating-IP bot traffic.
    """

    ANON_LIMIT          = 60
    APIKEY_LIMIT        = 180
    JWT_LIMIT           = 300
    PREDICT_ANON_LIMIT  = 20
    PREDICT_APIKEY_LIMIT = 80
    PREDICT_JWT_LIMIT   = 120
    WINDOW_SECONDS      = 60
    EVICT_INTERVAL      = 300  # run eviction pass every 5 minutes

    # Routes that bypass rate limiting completely
    _BYPASS = (
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/static",
        "/favicon",
        "/ws",
        "/webhook",
        "/api/public",
        "/notifications/ws",
    )

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

        # Determine the most specific stable key and corresponding limit
        api_key = request.headers.get("x-api-key", "")
        ip = request.client.host if request.client else "unknown"
        is_predict = "/predict" in path

        user_key = _extract_user_id(request)
        if user_key:
            key = user_key
            limit = self.PREDICT_JWT_LIMIT if is_predict else self.JWT_LIMIT
        elif api_key:
            key = f"key:{api_key}"
            limit = self.PREDICT_APIKEY_LIMIT if is_predict else self.APIKEY_LIMIT
        else:
            key = f"ip:{ip}"
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
