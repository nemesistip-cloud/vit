"""
In-memory TTL cache for expensive API endpoints.
Thread-safe, asyncio-compatible, zero external dependencies.
"""

import asyncio
import time
import functools
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class TTLCache:
    """Simple in-memory cache with per-key TTL expiry."""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        async with self._lock:
            self._store[key] = (value, time.monotonic() + ttl)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear_prefix(self, prefix: str) -> int:
        async with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]
            return len(keys)

    async def purge_expired(self) -> int:
        now = time.monotonic()
        async with self._lock:
            expired = [k for k, (_, exp) in self._store.items() if now > exp]
            for k in expired:
                del self._store[k]
            return len(expired)

    @property
    def size(self) -> int:
        return len(self._store)


# Global singleton
_cache = TTLCache()


def get_cache() -> TTLCache:
    return _cache


def cached(ttl: int = 60, key_prefix: str = ""):
    """
    Decorator for async functions. Caches the return value for `ttl` seconds.
    Cache key = prefix + str(args) + str(kwargs).

    Usage:
        @cached(ttl=30, key_prefix="dashboard:")
        async def expensive_fn(user_id: int): ...
    """
    def decorator(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}{fn.__name__}:{args}:{sorted(kwargs.items())}"
            cached_val = await _cache.get(cache_key)
            if cached_val is not None:
                return cached_val
            result = await fn(*args, **kwargs)
            await _cache.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator


async def cache_background_purge_loop(interval: int = 300):
    """Background coroutine to purge expired cache entries periodically."""
    while True:
        await asyncio.sleep(interval)
        purged = await _cache.purge_expired()
        if purged:
            logger.debug(f"Cache: purged {purged} expired entries, {_cache.size} remaining")
