"""app/api/middleware/rate_limit.py — HTTP rate-limiting middleware.

Strategy
--------
Every inbound request is keyed by the most specific identifier available,
in priority order:

    1. JWT user ID  (``user:{id}``)          — most precise; per-account limit
    2. API key      (``key:{api_key}``)       — trusted integrations get higher quota
    3. Client IP    (``ip:{address}``)        — anonymous / unauthenticated traffic

A *sliding-window* algorithm counts requests within the last 60 seconds.
When the count exceeds the tier's limit the middleware returns HTTP 429
before the request reaches any route handler.

Backend selection (lazy, one-time):
    - Redis available → Lua-scripted atomic sliding window (consistent across
      multiple app instances / horizontal scaling)
    - Redis unavailable → in-process deque per key (resets on restart; fine
      for single-instance dev deployments)

Bypass paths (no rate-limiting applied):
    /health, /docs, /openapi.json, /redoc, /static, /favicon,
    /ws, /webhook, /api/public, /notifications/ws

Limits per 60-second window:
    ┌─────────────────┬──────────────┬─────────────────┐
    │ Auth type       │ General req  │ /predict calls  │
    ├─────────────────┼──────────────┼─────────────────┤
    │ Anonymous (IP)  │     60       │      20         │
    │ API key         │    180       │      80         │
    │ JWT user        │    300       │     120         │
    └─────────────────┴──────────────┴─────────────────┘

Response headers added to every non-blocked response:
    X-RateLimit-Limit     — the applicable window limit
    X-RateLimit-Remaining — requests remaining in this window

SEC-07: idle in-memory buckets are evicted every 5 minutes to prevent
unbounded memory growth on long-running processes.
"""

from __future__ import annotations

import os
import time
import logging
from collections import defaultdict, deque
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.errors import error_response

log = logging.getLogger(__name__)

# In-memory buckets older than this (seconds) are evicted on the next sweep.
# Set to 2× the rate-limit window (60 s) so stale IPs don't accumulate.
_EVICT_AFTER_SECONDS = 120


# ── Feature flag ───────────────────────────────────────────────────────────────

def _rate_limiting_enabled() -> bool:
    """Return False when the ``RATE_LIMIT_ENABLED`` env var is set to ``false``.

    Allows disabling rate-limiting in automated test environments without
    changing code. Default is ``true`` (rate limiting always on).
    """
    return os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "false"


# ── JWT identity extractor ─────────────────────────────────────────────────────

def _extract_user_id(request: Request) -> str | None:
    """Decode the JWT in the Authorization header and return a stable user key.

    Performs a *non-validating* decode (no signature check) — we only need the
    subject claim to build a rate-limit key. Full validation is done by the
    auth dependency in each protected route.

    Returns:
        ``"user:{sub}"`` if a valid JWT with a subject claim is present,
        otherwise ``None`` (caller falls back to API-key or IP keying).
    """
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None  # Not a Bearer token — skip JWT extraction

    token = auth[7:]  # Strip the "Bearer " prefix
    try:
        import base64, json as _json
        parts = token.split(".")
        if len(parts) != 3:
            return None  # Not a valid JWT structure (header.payload.signature)

        # The payload segment may not be padded to a multiple of 4 — pad it.
        payload_b64 = parts[1] + "=="
        payload = _json.loads(base64.urlsafe_b64decode(payload_b64))

        # Try common subject claim names (JWT spec: "sub"; legacy: "user_id"/"id")
        uid = payload.get("sub") or payload.get("user_id") or payload.get("id")
        if uid:
            return f"user:{uid}"
    except Exception:
        pass  # Malformed JWT — fall through to IP-based keying

    return None


# ── Redis backend (lazy, initialised once) ─────────────────────────────────────
# Module-level singletons: the Redis client is created at most once per process.
# _redis_checked prevents repeated connection attempts on every request.

_redis_client = None
_redis_checked = False


def _get_redis():
    """Return the shared Redis async client, or None if Redis is unavailable.

    Called on the first request after startup. Subsequent calls return the
    cached result immediately (either a live client or None).

    The Redis URL is read from ``app.config.REDIS_URL`` (already sanitised)
    rather than ``os.getenv`` directly to guarantee consistent URL parsing.
    """
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client  # Already attempted — return cached result

    _redis_checked = True
    from app.config import REDIS_URL as redis_url
    if not redis_url:
        return None  # Redis not configured — use in-memory fallback silently

    try:
        import redis.asyncio as aioredis  # type: ignore
        # socket_timeout=0.5 s: if Redis is slow, we'd rather fall back to
        # in-memory than add latency to every request.
        _redis_client = aioredis.from_url(redis_url, decode_responses=True, socket_timeout=0.5)
        # Log only the host:port portion (after @) to avoid leaking credentials.
        log.info("Rate limiter: Redis backend enabled (%s)", redis_url.split("@")[-1])
    except Exception as exc:
        log.warning("Rate limiter: Redis unavailable (%s) — using in-memory fallback", exc)
        _redis_client = None

    return _redis_client


# ── Redis sliding-window counter ───────────────────────────────────────────────

async def _redis_sliding_window(redis, key: str, limit: int, window: int) -> tuple[bool, int, int]:
    """Atomically check and increment a sliding-window counter in Redis.

    Uses a Lua script so the read-modify-write is atomic — no race condition
    is possible even under concurrent requests from the same client.

    The counter is stored as a Redis sorted set (ZSET) where each member is a
    unique timestamp string and the score is the timestamp in milliseconds.
    Old entries (outside the window) are pruned on every call.

    Args:
        redis:  An active aioredis client instance.
        key:    The rate-limit bucket key, e.g. ``"rl:user:42"``.
        limit:  Maximum number of requests allowed in ``window`` seconds.
        window: Sliding-window size in seconds (typically 60).

    Returns:
        Tuple of (allowed, remaining, retry_after_seconds):
        - allowed:       True if the request should proceed.
        - remaining:     Requests left in the current window (0 when blocked).
        - retry_after:   Seconds until the oldest entry expires (0 when allowed).
    """
    now_ms       = int(time.time() * 1000)   # Current time in milliseconds
    window_ms    = window * 1000              # Window size in milliseconds
    clear_before = now_ms - window_ms         # Prune all entries older than this

    # Lua script — executed atomically on the Redis server.
    # KEYS[1] = bucket key; ARGV[1..4] = now_ms, window_ms, clear_before, limit
    lua_script = """
local key         = KEYS[1]
local now         = tonumber(ARGV[1])
local window_ms   = tonumber(ARGV[2])
local clear_before = tonumber(ARGV[3])
local limit       = tonumber(ARGV[4])

-- Remove entries that have fallen outside the sliding window
redis.call('ZREMRANGEBYSCORE', key, '-inf', clear_before)

local count = redis.call('ZCARD', key)
if count < limit then
    -- Under limit: add this request as a scored member (score = timestamp)
    -- Append a random suffix to the member name to avoid key collisions when
    -- two requests arrive at the exact same millisecond.
    redis.call('ZADD', key, now, now .. '-' .. math.random(1e9))
    -- Expire the set after 2× window so it auto-cleans on idle keys
    redis.call('PEXPIRE', key, window_ms * 2)
    return {1, limit - count - 1, 0}  -- {allowed, remaining, retry_after}
else
    -- Over limit: find the oldest entry to compute retry_after
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry  = math.ceil((tonumber(oldest[2]) + window_ms - now) / 1000) + 1
    return {0, 0, retry}  -- {blocked, 0 remaining, retry_after}
end
"""
    try:
        result = await redis.eval(lua_script, 1, key, now_ms, window_ms, clear_before, limit)
        allowed     = bool(result[0])
        remaining   = int(result[1])
        retry_after = int(result[2])
        return allowed, remaining, retry_after
    except Exception as exc:
        # Redis error mid-request: fail open (allow the request) rather than
        # blocking all traffic due to an infrastructure hiccup.
        log.warning("Redis sliding window error: %s — allowing request", exc)
        return True, limit, 0


# ── Middleware class ───────────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces sliding-window rate limits.

    Registered in main.py via ``app.add_middleware(RateLimitMiddleware)``.
    Runs before every route handler and auth dependency.

    The middleware is deliberately simple: it only inspects the Authorization
    header (non-validating JWT decode) and X-Api-Key header. Full token
    validation still happens in the route's dependency chain.
    """

    # ── Per-tier request limits (per 60-second window) ──────────────────────
    ANON_LIMIT           = 60    # Unauthenticated clients (IP-keyed)
    APIKEY_LIMIT         = 180   # Trusted integrations (API-key-keyed)
    JWT_LIMIT            = 300   # Logged-in users (user-ID-keyed)

    # Prediction endpoints get a separate, tighter limit to protect AI inference costs
    PREDICT_ANON_LIMIT   = 20
    PREDICT_APIKEY_LIMIT = 80
    PREDICT_JWT_LIMIT    = 120

    WINDOW_SECONDS = 60   # Sliding window duration (seconds)
    EVICT_INTERVAL = 300  # How often to sweep stale in-memory buckets (seconds)

    # Prefixes that skip rate-limiting entirely.
    # Kept as a tuple for fast ``str.startswith()`` check.
    _BYPASS = (
        "/health",           # Load-balancer probes must never be rate-limited
        "/docs",             # Swagger UI assets
        "/openapi.json",     # OpenAPI schema fetch
        "/redoc",            # ReDoc UI
        "/static",           # Vite-built frontend assets
        "/favicon",          # Browser icon fetches
        "/ws",               # WebSocket handshakes (rate-limit at the WS layer instead)
        "/webhook",          # Payment webhooks from Stripe/Paystack (IP-trusted)
        "/api/public",       # Landing page data, public config — must be fast
        "/notifications/ws", # Real-time notification socket upgrade
    )

    def __init__(self, app) -> None:
        super().__init__(app)
        # In-memory fallback: one deque per rate-limit key (stores request timestamps)
        self._buckets: dict = defaultdict(deque)
        # Tracks the last-seen time per key so stale buckets can be evicted
        self._last_seen: dict = {}
        # Timestamp of the last eviction sweep
        self._last_evict: float = time.time()

    # ── In-memory helpers ────────────────────────────────────────────────────

    def _evict_stale(self, now: float) -> None:
        """Remove buckets that have been idle longer than ``_EVICT_AFTER_SECONDS``.

        Called on every request but only does real work every ``EVICT_INTERVAL``
        seconds to avoid scanning the whole dict on every single request.
        """
        if now - self._last_evict < self.EVICT_INTERVAL:
            return  # Too soon — skip this sweep

        self._last_evict = now
        cutoff = now - _EVICT_AFTER_SECONDS
        # Collect stale keys first, then delete — avoids mutating dict during iteration
        stale = [k for k, ts in self._last_seen.items() if ts < cutoff]
        for k in stale:
            self._buckets.pop(k, None)
            self._last_seen.pop(k, None)

    def _in_memory_check(self, key: str, limit: int, now: float) -> tuple[bool, int, int]:
        """Sliding-window check using an in-process deque.

        Timestamps older than ``WINDOW_SECONDS`` are discarded from the left
        of the deque. If the count after pruning equals or exceeds ``limit``
        the request is blocked.

        Args:
            key:   Rate-limit bucket identifier (e.g. ``"ip:1.2.3.4"``).
            limit: Maximum requests allowed in the window.
            now:   Current monotonic timestamp (float seconds).

        Returns:
            Tuple of (allowed, remaining, retry_after_seconds).
        """
        self._last_seen[key] = now       # Update idle tracker
        self._evict_stale(now)           # Opportunistic sweep of dead buckets

        window_start = now - self.WINDOW_SECONDS
        bucket = self._buckets[key]

        # Prune expired entries from the front of the deque (oldest first)
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= limit:
            # Blocked: tell the client when their oldest entry expires
            retry_after = int(self.WINDOW_SECONDS - (now - bucket[0])) + 1
            return False, 0, retry_after

        # Allowed: record this request timestamp and return remaining quota
        bucket.append(now)
        return True, max(0, limit - len(bucket)), 0

    # ── Main dispatch ────────────────────────────────────────────────────────

    async def dispatch(self, request: Request, call_next):
        """Intercept every HTTP request and enforce rate limits.

        Flow:
            1. Feature-flag check — bypass if RATE_LIMIT_ENABLED=false
            2. Bypass check — skip whitelisted path prefixes
            3. Identity resolution — JWT > API key > IP
            4. Limit resolution — predict vs general × tier
            5. Counter check — Redis (if available) or in-memory
            6. Block (429) or pass through, attaching rate-limit headers
        """
        # Step 1: Feature flag — allows disabling in test environments
        if not _rate_limiting_enabled():
            return await call_next(request)

        path = request.url.path

        # Step 2: Bypass for paths that must never be rate-limited
        if any(path.startswith(b) for b in self._BYPASS):
            # WebSocket upgrades on bypass paths still pass through untouched
            return await call_next(request)

        # Step 3: Resolve the best available identity for this request
        api_key    = request.headers.get("x-api-key", "")
        ip         = request.client.host if request.client else "unknown"
        is_predict = "/predict" in path  # Tighter limits apply to AI inference

        user_key = _extract_user_id(request)
        if user_key:
            # Authenticated user — highest quota, keyed by stable user ID
            key   = user_key
            limit = self.PREDICT_JWT_LIMIT if is_predict else self.JWT_LIMIT
        elif api_key:
            # API-key client — mid-tier quota, keyed by the API key itself
            key   = f"key:{api_key}"
            limit = self.PREDICT_APIKEY_LIMIT if is_predict else self.APIKEY_LIMIT
        else:
            # Anonymous — lowest quota, keyed by IP address
            key   = f"ip:{ip}"
            limit = self.PREDICT_ANON_LIMIT if is_predict else self.ANON_LIMIT

        # Step 4 & 5: Check the counter in Redis or fall back to in-memory
        redis = _get_redis()
        now   = time.time()

        if redis is not None:
            # Redis path: atomic Lua sliding window, survives multiple instances
            redis_key = f"rl:{key}"
            allowed, remaining, retry_after = await _redis_sliding_window(
                redis, redis_key, limit, self.WINDOW_SECONDS
            )
        else:
            # In-memory path: deque per key, resets on restart
            allowed, remaining, retry_after = self._in_memory_check(key, limit, now)

        # Step 6a: Block — return 429 with Retry-After header
        if not allowed:
            return error_response(
                request=request,
                status_code=429,
                code="rate_limit_exceeded",
                message="Rate limit exceeded. Please slow down.",
                details={
                    "limit":          limit,
                    "window_seconds": self.WINDOW_SECONDS,
                    "retry_after":    retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Step 6b: Pass through — add informational rate-limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"]     = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
