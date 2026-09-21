"""app/core/rate_limit.py
Redis-backed login rate limiter and per-user prediction rate limiter.
Falls back gracefully to in-memory when Redis is unavailable.

Login limiter:  sliding window via Redis sorted sets (ZADD / ZREMRANGEBYSCORE).
Prediction limiter: atomic INCR + EXPIREAT at UTC midnight per user per day.
Both preserve the original public API so no callers need to change.
"""

import asyncio
import concurrent.futures
import logging
import time
from collections import defaultdict
from datetime import date as _date, datetime, timezone, timedelta
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300   # 5-minute sliding window
LOCKOUT_SECONDS = 900  # 15-minute lockout


# ── Redis access ──────────────────────────────────────────────────────────────

def _get_redis():
    """Return the global async Redis client, or None if unavailable."""
    try:
        from app.core.redis import redis_client  # noqa: PLC0415
        return redis_client
    except Exception:
        return None


def _run_async_safe(coro):
    """
    Run an async coroutine from a sync caller, regardless of whether an event
    loop is already running (as it always is inside a FastAPI request).

    Strategy: submit the coroutine to the *running* loop via
    run_coroutine_threadsafe from the current thread, then block until the
    result is ready.  This avoids "This event loop is already running" errors
    and re-uses the existing loop so Redis connection pools are shared.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=2.0)
        return loop.run_until_complete(coro)
    except concurrent.futures.TimeoutError:
        logger.warning("Redis operation timed out (2 s) — falling back to in-memory")
        raise
    except Exception:
        raise


# ── In-memory fallback ────────────────────────────────────────────────────────

class _AttemptStore:
    def __init__(self):
        self._lock = Lock()
        self._timestamps: dict[str, list[float]] = defaultdict(list)

    def _prune(self, key: str, now: float):
        cutoff = now - WINDOW_SECONDS
        self._timestamps[key] = [t for t in self._timestamps[key] if t > cutoff]

    def record_failure(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            self._timestamps[key].append(now)
            count = len(self._timestamps[key])
        if count >= MAX_ATTEMPTS:
            logger.warning(
                "Login rate-limit triggered for key=%s (attempts=%d) [in-memory]", key, count
            )
        return count

    def is_locked(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            return len(self._timestamps[key]) >= MAX_ATTEMPTS

    def clear(self, key: str):
        with self._lock:
            self._timestamps.pop(key, None)


_store = _AttemptStore()


# ── Redis sliding-window helpers (login) ──────────────────────────────────────

async def _redis_record_failure(redis, key: str) -> int:
    """Atomic sliding-window failure record using a sorted set. Returns attempt count."""
    rkey = f"login_attempts:{key}"
    now = time.time()
    cutoff = now - WINDOW_SECONDS
    pipe = redis.pipeline()
    pipe.zremrangebyscore(rkey, "-inf", cutoff)
    pipe.zadd(rkey, {str(now): now})
    pipe.zcard(rkey)
    pipe.expire(rkey, LOCKOUT_SECONDS)
    results = await pipe.execute()
    count = results[2]
    if count >= MAX_ATTEMPTS:
        logger.warning(
            "Login rate-limit triggered for key=%s (attempts=%d) [Redis]", key, count
        )
    return count


async def _redis_is_locked(redis, key: str) -> bool:
    """Check whether key has exceeded the sliding-window limit."""
    rkey = f"login_attempts:{key}"
    now = time.time()
    cutoff = now - WINDOW_SECONDS
    pipe = redis.pipeline()
    pipe.zremrangebyscore(rkey, "-inf", cutoff)
    pipe.zcard(rkey)
    results = await pipe.execute()
    return results[1] >= MAX_ATTEMPTS


async def _redis_clear_login(redis, key: str):
    await redis.delete(f"login_attempts:{key}")


# ── Public login rate-limit API ───────────────────────────────────────────────

def check_login_allowed(email: Optional[str], ip: Optional[str] = None):
    """Raise ValueError if the email or IP is currently rate-limited."""
    redis = _get_redis()
    if redis is not None:
        try:
            if email and _run_async_safe(_redis_is_locked(redis, email.lower())):
                raise ValueError(
                    f"Too many failed login attempts. Account temporarily locked for "
                    f"{LOCKOUT_SECONDS // 60} minutes."
                )
            if ip and _run_async_safe(_redis_is_locked(redis, ip)):
                raise ValueError(
                    f"Too many failed login attempts from this IP. "
                    f"Try again in {LOCKOUT_SECONDS // 60} minutes."
                )
            return
        except ValueError:
            raise
        except Exception as exc:
            logger.warning(
                "Redis login check failed — falling back to in-memory: %s", exc
            )

    # In-memory fallback
    if email and _store.is_locked(email.lower()):
        raise ValueError(
            f"Too many failed login attempts. Account temporarily locked for "
            f"{LOCKOUT_SECONDS // 60} minutes."
        )
    if ip and _store.is_locked(ip):
        raise ValueError(
            f"Too many failed login attempts from this IP. "
            f"Try again in {LOCKOUT_SECONDS // 60} minutes."
        )


def record_login_failure(email: Optional[str], ip: Optional[str] = None):
    """Record a failed login attempt for the given email and/or IP."""
    redis = _get_redis()
    if redis is not None:
        try:
            if email:
                _run_async_safe(_redis_record_failure(redis, email.lower()))
            if ip:
                _run_async_safe(_redis_record_failure(redis, ip))
            return
        except Exception as exc:
            logger.warning(
                "Redis login failure record failed — falling back to in-memory: %s", exc
            )

    if email:
        _store.record_failure(email.lower())
    if ip:
        _store.record_failure(ip)


def clear_login_failures(email: Optional[str]):
    """Clear all recorded failures for the given email (e.g. on successful login)."""
    redis = _get_redis()
    if redis is not None:
        try:
            if email:
                _run_async_safe(_redis_clear_login(redis, email.lower()))
            return
        except Exception as exc:
            logger.warning(
                "Redis clear login failures failed — falling back to in-memory: %s", exc
            )

    if email:
        _store.clear(email.lower())


# ── Per-user prediction rate limiter ─────────────────────────────────────────

_pred_lock = Lock()
_pred_counts: dict[int, dict] = {}


def _pred_today() -> str:
    return _date.today().isoformat()


def get_limit_for_tier(tier: str) -> int:
    """Return the daily prediction limit based on user tier."""
    from app.config import MAX_PREDICTIONS_PER_DAY  # noqa: PLC0415

    tier = (tier or "free").lower()
    if tier in ("pro", "analyst"):
        return 100
    if tier == "elite":
        return 500
    return MAX_PREDICTIONS_PER_DAY


def _pred_redis_key(user_id: int) -> str:
    return f"pred_count:{user_id}:{_pred_today()}"


async def _redis_check_prediction(
    redis, user_id: int, limit: int
) -> tuple[bool, int, int, str]:
    """Return (allowed, current_count, limit, resets_at_iso)."""
    key = _pred_redis_key(user_id)
    tomorrow = (_date.today() + timedelta(days=1)).isoformat() + "T00:00:00Z"
    raw = await redis.get(key)
    count = int(raw) if raw else 0
    return count < limit, count, limit, tomorrow


async def _redis_record_prediction(redis, user_id: int) -> int:
    """Atomically increment daily prediction count with auto-expiry at UTC midnight."""
    key = _pred_redis_key(user_id)
    # TTL = seconds remaining until next UTC midnight
    now_utc = datetime.now(timezone.utc)
    tomorrow_utc = (now_utc + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    ttl = max(1, int((tomorrow_utc - now_utc).total_seconds()) + 1)
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, ttl)
    results = await pipe.execute()
    return results[0]


def check_prediction_limit(user_id: int, tier: str = "free") -> tuple[bool, int, int, str]:
    """
    Returns (allowed, current_count, limit, resets_at_utc_iso).
    Checks Redis first; falls back to in-memory on failure.
    """
    if user_id is None:
        return True, 0, 9999, ""

    limit = get_limit_for_tier(tier)
    today = _pred_today()
    tomorrow = (_date.today() + timedelta(days=1)).isoformat() + "T00:00:00Z"

    redis = _get_redis()
    if redis is not None:
        try:
            return _run_async_safe(_redis_check_prediction(redis, user_id, limit))
        except Exception as exc:
            logger.warning(
                "Redis prediction check failed — falling back to in-memory: %s", exc
            )

    # In-memory fallback
    with _pred_lock:
        rec = _pred_counts.get(user_id)
        if rec is None or rec["date"] != today:
            _pred_counts[user_id] = {"date": today, "count": 0}
            rec = _pred_counts[user_id]
        return rec["count"] < limit, rec["count"], limit, tomorrow


def record_prediction(user_id: int) -> int:
    """Increment and return the new daily count for user_id."""
    if user_id is None:
        return 0

    redis = _get_redis()
    if redis is not None:
        try:
            return _run_async_safe(_redis_record_prediction(redis, user_id))
        except Exception as exc:
            logger.warning(
                "Redis prediction record failed — falling back to in-memory: %s", exc
            )

    # In-memory fallback
    today = _pred_today()
    with _pred_lock:
        rec = _pred_counts.get(user_id)
        if rec is None or rec["date"] != today:
            _pred_counts[user_id] = {"date": today, "count": 0}
        _pred_counts[user_id]["count"] += 1
        return _pred_counts[user_id]["count"]
