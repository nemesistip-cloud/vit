"""app/services/cache.py — Async Redis cache with in-memory fallback.

Provides a simple get/set/delete interface and a `cached()` decorator for
FastAPI route handlers. Falls back to an in-process TTL dict when Redis is
unavailable so the app works in any environment.

Usage:
    from app.services.cache import cache, cached

    # Direct use
    await cache.set("key", {"data": 1}, ttl=60)
    value = await cache.get("key")
    await cache.delete("key")
    await cache.delete_pattern("matches:*")

    # Decorator (caches the entire route response for ttl seconds)
    @router.get("/matches")
    @cached("matches:list", ttl=30)
    async def list_matches(...):
        ...
"""
from __future__ import annotations

import json
import logging
import os
import time
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory fallback store
# ---------------------------------------------------------------------------

class _MemoryStore:
    """Thread-safe in-process TTL dict — used when Redis is unavailable."""
    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at and time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = (time.monotonic() + ttl) if ttl else 0.0
        self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def delete_pattern(self, pattern: str) -> int:
        prefix = pattern.rstrip("*")
        keys = [k for k in list(self._store) if k.startswith(prefix)]
        for k in keys:
            del self._store[k]
        return len(keys)

    def flush(self) -> None:
        self._store.clear()


_memory = _MemoryStore()

# ---------------------------------------------------------------------------
# Redis client (lazy-initialised)
# ---------------------------------------------------------------------------

_redis_client = None
_redis_checked = False


def _get_redis():
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return None
    try:
        import redis.asyncio as aioredis   # type: ignore
        _redis_client = aioredis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=0.5,
            socket_connect_timeout=1.0,
        )
        logger.info("Cache: Redis backend enabled")
    except Exception as exc:
        logger.warning("Cache: Redis unavailable (%s) — using memory fallback", exc)
        _redis_client = None
    return _redis_client


# ---------------------------------------------------------------------------
# Cache class
# ---------------------------------------------------------------------------

class Cache:
    """Async cache with Redis primary and in-memory fallback."""

    async def get(self, key: str) -> Optional[Any]:
        r = _get_redis()
        if r is not None:
            try:
                raw = await r.get(key)
                if raw is None:
                    return None
                return json.loads(raw)
            except Exception as exc:
                logger.debug("Cache.get Redis error (%s) — falling back", exc)
        return _memory.get(key)

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        serialised = json.dumps(value, default=str)
        r = _get_redis()
        if r is not None:
            try:
                await r.set(key, serialised, ex=ttl)
                return
            except Exception as exc:
                logger.debug("Cache.set Redis error (%s) — falling back", exc)
        _memory.set(key, value, ttl=ttl)

    async def delete(self, key: str) -> None:
        r = _get_redis()
        if r is not None:
            try:
                await r.delete(key)
                return
            except Exception as exc:
                logger.debug("Cache.delete Redis error (%s) — falling back", exc)
        _memory.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        r = _get_redis()
        if r is not None:
            try:
                keys = await r.keys(pattern)
                if keys:
                    await r.delete(*keys)
                return len(keys)
            except Exception as exc:
                logger.debug("Cache.delete_pattern Redis error (%s) — falling back", exc)
        return _memory.delete_pattern(pattern)

    async def flush(self) -> None:
        r = _get_redis()
        if r is not None:
            try:
                await r.flushdb()
                return
            except Exception as exc:
                logger.debug("Cache.flush Redis error (%s) — falling back", exc)
        _memory.flush()

    async def get_or_set(self, key: str, fn: Callable, ttl: int = 60) -> Any:
        """Return cached value or compute via fn() and cache it."""
        cached_val = await self.get(key)
        if cached_val is not None:
            return cached_val
        value = await fn()
        if value is not None:
            await self.set(key, value, ttl=ttl)
        return value


cache = Cache()


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def cached(key_template: str, ttl: int = 60):
    """
    Decorator that caches a FastAPI async route's return value.

    key_template supports simple {param} substitution from the function's
    keyword arguments, e.g. cached("match:{match_id}", ttl=30).
    """
    def decorator(fn: Callable):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            try:
                key = key_template.format(**kwargs)
            except KeyError:
                key = key_template
            hit = await cache.get(key)
            if hit is not None:
                return hit
            result = await fn(*args, **kwargs)
            if result is not None:
                try:
                    await cache.set(key, result, ttl=ttl)
                except Exception:
                    pass
            return result
        return wrapper
    return decorator
