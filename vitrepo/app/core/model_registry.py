"""app/core/model_registry.py — Lazy-loading ML model registry with LRU eviction.

RAM Budget (env vars, defaults in app/config.py):
  MAX_PROCESS_RAM_MB      evict before loading when RSS > this (default 400)
  MAX_LOADED_MODELS       max models kept in cache at once   (default 3)
  MODEL_CACHE_TTL_SECONDS evict models idle longer than this (default 300)

Usage::

    from app.core.model_registry import registry

    payload = await registry.get("xgb_v2")   # lazy, LRU-cached
    await registry.unload("xgb_v2")           # manual eviction
    status  = registry.status()               # JSON-serialisable snapshot
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _slog(level: str, event: str, **kw) -> None:
    msg = json.dumps({"ts": time.time(), "event": event, **kw})
    getattr(logger, level)(msg)


class ModelRegistry:
    """Lazy-load, LRU-evict, RAM-pressure-aware ML model registry."""

    def __init__(self) -> None:
        # OrderedDict: front = LRU, end = MRU
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._load_times: Dict[str, float] = {}
        self._last_used: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._key_locks: Dict[str, asyncio.Lock] = {}

    # ── Public interface ────────────────────────────────────────────────────

    async def get(self, model_name: str) -> Optional[Any]:
        """Return a model payload; load from disk on first call.

        Returns None (never raises) when the pkl is missing.
        Callers fall back to the algorithmic model.
        """
        # Fast path — already in cache
        if model_name in self._cache:
            self._last_used[model_name] = time.monotonic()
            self._cache.move_to_end(model_name)
            return self._cache[model_name]

        # Ensure per-key lock exists
        async with self._lock:
            if model_name not in self._key_locks:
                self._key_locks[model_name] = asyncio.Lock()

        async with self._key_locks[model_name]:
            # Re-check after acquiring key lock
            if model_name in self._cache:
                self._last_used[model_name] = time.monotonic()
                return self._cache[model_name]

            # Free RAM before loading
            if await self.memory_pressure():
                _slog("warning", "memory_pressure_before_load",
                      model=model_name, action="evict_lru")
                await self.evict_lru()

            # Enforce MAX_LOADED_MODELS cap
            max_models = _cfg("MAX_LOADED_MODELS", 3)
            async with self._lock:
                while len(self._cache) >= max_models:
                    evicted = next(iter(self._cache))
                    self._cache.pop(evicted, None)
                    self._load_times.pop(evicted, None)
                    self._last_used.pop(evicted, None)
                    _slog("info", "evict_cap", model=evicted,
                          reason=f"MAX_LOADED_MODELS={max_models}")

            # Load from disk in a thread (blocking I/O)
            payload = await asyncio.get_event_loop().run_in_executor(
                None, _load_from_disk, model_name
            )
            if payload is None:
                _slog("warning", "model_not_found", model=model_name)
                return None

            now = time.monotonic()
            async with self._lock:
                self._cache[model_name] = payload
                self._load_times[model_name] = now
                self._last_used[model_name] = now

            _slog("info", "model_loaded", model=model_name,
                  ram_mb=round(_process_ram_mb(), 1))
            return payload

    async def unload(self, model_name: str) -> None:
        """Evict a model from cache to free RAM. Never raises."""
        try:
            async with self._lock:
                removed = self._cache.pop(model_name, None)
                self._load_times.pop(model_name, None)
                self._last_used.pop(model_name, None)
            if removed is not None:
                _slog("info", "model_unloaded", model=model_name,
                      ram_mb=round(_process_ram_mb(), 1))
        except Exception as exc:
            _slog("error", "unload_error", model=model_name, error=str(exc))

    async def memory_pressure(self) -> bool:
        """True when process RSS > MAX_PROCESS_RAM_MB."""
        return _process_ram_mb() > _cfg("MAX_PROCESS_RAM_MB", 400)

    async def evict_lru(self) -> None:
        """Evict the least recently used model. Never raises."""
        try:
            async with self._lock:
                if not self._cache:
                    return
                lru_key = next(iter(self._cache))
                self._cache.pop(lru_key, None)
                self._load_times.pop(lru_key, None)
                last = self._last_used.pop(lru_key, 0)
            idle_s = round(time.monotonic() - last, 1)
            _slog("info", "evict_lru", model=lru_key,
                  idle_s=idle_s, ram_mb=round(_process_ram_mb(), 1))
        except Exception as exc:
            _slog("error", "evict_lru_error", error=str(exc))

    async def evict_stale(self) -> int:
        """Evict models idle > MODEL_CACHE_TTL_SECONDS. Returns count."""
        ttl = _cfg("MODEL_CACHE_TTL_SECONDS", 300)
        now = time.monotonic()
        stale = [k for k, t in list(self._last_used.items()) if (now - t) > ttl]
        for k in stale:
            await self.unload(k)
        if stale:
            _slog("info", "evict_stale", models=stale, ttl_s=ttl)
        return len(stale)

    def status(self) -> Dict[str, Any]:
        """JSON-serialisable snapshot of loaded models and RAM usage."""
        now = time.monotonic()
        return {
            "loaded_models": list(self._cache.keys()),
            "count": len(self._cache),
            "ram_mb": round(_process_ram_mb(), 1),
            "max_ram_mb": _cfg("MAX_PROCESS_RAM_MB", 400),
            "max_loaded": _cfg("MAX_LOADED_MODELS", 3),
            "ttl_seconds": _cfg("MODEL_CACHE_TTL_SECONDS", 300),
            "models": {
                k: {
                    "loaded_s_ago": round(now - self._load_times.get(k, now), 1),
                    "idle_s":       round(now - self._last_used.get(k, now), 1),
                }
                for k in self._cache
            },
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _process_ram_mb() -> float:
    """Current process RSS in MB. Returns 0.0 when psutil unavailable."""
    try:
        import psutil, os as _os
        return psutil.Process(_os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def _cfg(name: str, default: int) -> int:
    try:
        from app.config import get_int_env
        return get_int_env(name, str(default))
    except ImportError:
        try:
            return int(os.environ.get(name, str(default)))
        except (TypeError, ValueError):
            return default


def _load_from_disk(model_name: str) -> Optional[Dict[str, Any]]:
    """Blocking disk load — executed via run_in_executor to avoid blocking the loop."""
    try:
        from services.ml_service.model_loader import load_model
        return load_model(model_name, cache_enabled=False)
    except Exception as exc:
        _slog("error", "disk_load_error", model=model_name, error=str(exc))
        return None


# ── Global singleton ──────────────────────────────────────────────────────────

registry = ModelRegistry()
