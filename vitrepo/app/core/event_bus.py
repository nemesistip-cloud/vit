"""
app/core/event_bus.py — VIT Platform Event Bus

Phase 0 upgrade: dual-layer event bus.

  1. In-process layer  — asyncio handlers, zero latency, used within the gateway
  2. Redis pub/sub layer — cross-service events that survive restarts and can be
                           consumed by vit-ai, vit-storage, and future services

Standard event schema:
    {
        "event_type":   "prediction.completed",
        "source":       "vitnetwork",
        "payload":      { ... },
        "timestamp":    "2026-07-11T21:00:00Z",
        "correlation_id": "req-abc123"   # optional
    }

Usage:
    from app.core.event_bus import event_bus

    # publish (in-process + Redis if configured)
    await event_bus.publish("prediction.completed", {"match_id": 42}, sender="predictor")

    # subscribe in-process
    event_bus.subscribe("user.registered", my_async_handler)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Event model ───────────────────────────────────────────────────────────────

@dataclass
class Event:
    name: str
    payload: Dict[str, Any]
    sender: str
    correlation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_wire(self) -> str:
        """Serialize to JSON for Redis transport."""
        return json.dumps({
            "event_type":     self.name,
            "source":         self.sender,
            "payload":        self.payload,
            "correlation_id": self.correlation_id,
            "timestamp":      self.timestamp.isoformat(),
        })

    @classmethod
    def from_wire(cls, raw: str) -> "Event":
        d = json.loads(raw)
        return cls(
            name=d.get("event_type", "unknown"),
            payload=d.get("payload", {}),
            sender=d.get("source", "unknown"),
            correlation_id=d.get("correlation_id"),
        )


# ── Bus implementation ────────────────────────────────────────────────────────

Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    """Centralized asynchronous event bus for the VIT Platform."""

    _instance: Optional["EventBus"] = None

    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._subscribers: Dict[str, List[Handler]] = {}
            inst._global_subscribers: List[Handler] = []
            inst._redis: Any = None
            inst._redis_channel: str = "vit:events"
            inst._redis_enabled: bool = False
            cls._instance = inst
        return cls._instance

    # ── Subscription API ──────────────────────────────────────────────────────

    def subscribe(self, event_name: str, handler: Handler) -> None:
        """Subscribe to a specific event (in-process only)."""
        self._subscribers.setdefault(event_name, []).append(handler)
        logger.debug("[event_bus] subscribed handler to '%s'", event_name)

    def subscribe_all(self, handler: Handler) -> None:
        """Subscribe to every event (in-process only)."""
        self._global_subscribers.append(handler)
        logger.debug("[event_bus] subscribed global handler")

    # ── Publish API ───────────────────────────────────────────────────────────

    async def publish(
        self,
        event_name: str,
        payload: Dict[str, Any],
        sender: str = "system",
        correlation_id: Optional[str] = None,
    ) -> None:
        """Publish an event — dispatched in-process and pushed to Redis."""
        event = Event(
            name=event_name,
            payload=payload,
            sender=sender,
            correlation_id=correlation_id,
        )

        await self._dispatch_local(event)
        await self._publish_redis(event)

    # ── Redis layer ───────────────────────────────────────────────────────────

    async def connect_redis(self, redis_url: Optional[str] = None) -> None:
        """Connect the Redis pub/sub layer. Safe to call multiple times."""
        url = redis_url or os.getenv("REDIS_URL", "")
        if not url:
            logger.info("[event_bus] REDIS_URL not set — Redis pub/sub disabled")
            return
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(url, decode_responses=True)
            await self._redis.ping()
            self._redis_enabled = True
            logger.info("[event_bus] Redis pub/sub connected on channel '%s'", self._redis_channel)
        except Exception as exc:
            logger.warning("[event_bus] Redis connect failed: %s — pub/sub disabled", exc)
            self._redis = None
            self._redis_enabled = False

    async def disconnect_redis(self) -> None:
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None
            self._redis_enabled = False

    async def _publish_redis(self, event: Event) -> None:
        if not self._redis_enabled or self._redis is None:
            return
        try:
            await self._redis.publish(self._redis_channel, event.to_wire())
        except Exception as exc:
            logger.warning("[event_bus] Redis publish failed for '%s': %s", event.name, exc)

    # ── In-process dispatch ───────────────────────────────────────────────────

    async def _dispatch_local(self, event: Event) -> None:
        handlers: List[Handler] = (
            self._subscribers.get(event.name, []) + self._global_subscribers
        )
        if handlers:
            await asyncio.gather(*[self._safe_call(h, event) for h in handlers])
        else:
            logger.debug("[event_bus] no local subscribers for '%s'", event.name)

    async def _safe_call(self, handler: Handler, event: Event) -> None:
        try:
            await handler(event)
        except Exception as exc:
            logger.error(
                "[event_bus] handler error for '%s': %s", event.name, exc, exc_info=True
            )

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "redis_enabled":    self._redis_enabled,
            "redis_channel":    self._redis_channel,
            "event_types":      list(self._subscribers.keys()),
            "global_handlers":  len(self._global_subscribers),
        }


# ── Global singleton ──────────────────────────────────────────────────────────

event_bus = EventBus()
