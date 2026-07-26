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
import uuid
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
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_wire(self) -> str:
        """Serialize to JSON for Redis transport."""
        return json.dumps({
            "event_type":     self.name,
            "source":         self.sender,
            "payload":        self.payload,
            "correlation_id": self.correlation_id,
            "request_id":     self.request_id,
            "event_id":       self.event_id,
            "metadata":       self.metadata,
            "version":        self.version,
            "timestamp":      self.timestamp.isoformat(),
        })

    @classmethod
    def from_wire(cls, raw: str) -> "Event":
        d = json.loads(raw)
        timestamp = d.get("timestamp")
        ts = None
        if timestamp:
            try:
                ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                ts = datetime.now(timezone.utc)
        return cls(
            name=d.get("event_type", "unknown"),
            payload=d.get("payload", {}),
            sender=d.get("source", "unknown"),
            correlation_id=d.get("correlation_id"),
            event_id=d.get("event_id", uuid.uuid4().hex),
            request_id=d.get("request_id"),
            metadata=d.get("metadata", {}),
            version=d.get("version", 1),
            timestamp=ts or datetime.now(timezone.utc),
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
            inst._history: Dict[str, List[Event]] = {}
            inst._dead_letters: List[Dict[str, Any]] = []
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
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        version: int = 1,
        max_retries: int = 0,
        retry_delay: float = 0.0,
    ) -> Event:
        """Publish an event — dispatched in-process and pushed to Redis."""
        event = Event(
            name=event_name,
            payload=payload,
            sender=sender,
            correlation_id=correlation_id,
            request_id=request_id,
            metadata=metadata or {},
            version=version,
        )

        self._history.setdefault(event_name, []).append(event)
        await self._dispatch_local(event, max_retries=max_retries, retry_delay=retry_delay)
        await self._publish_redis(event)
        return event

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

    async def _dispatch_local(
        self,
        event: Event,
        max_retries: int = 0,
        retry_delay: float = 0.0,
    ) -> None:
        handlers: List[Handler] = (
            self._subscribers.get(event.name, []) + self._global_subscribers
        )
        if handlers:
            await asyncio.gather(*[
                self._safe_call(h, event, max_retries=max_retries, retry_delay=retry_delay)
                for h in handlers
            ])
        else:
            logger.debug("[event_bus] no local subscribers for '%s'", event.name)

    async def _safe_call(
        self,
        handler: Handler,
        event: Event,
        max_retries: int = 0,
        retry_delay: float = 0.0,
    ) -> None:
        attempt = 0
        while True:
            try:
                await handler(event)
                return
            except Exception as exc:
                attempt += 1
                if attempt > max_retries:
                    self._dead_letters.append({
                        "event_name": event.name,
                        "event_id": event.event_id,
                        "error": str(exc),
                        "attempts": attempt,
                    })
                    logger.error(
                        "[event_bus] handler error for '%s': %s", event.name, exc, exc_info=True
                    )
                    return
                logger.warning(
                    "[event_bus] handler error for '%s' (retry %s/%s): %s",
                    event.name,
                    attempt,
                    max_retries,
                    exc,
                )
                if retry_delay > 0:
                    await asyncio.sleep(retry_delay)

    # ── Diagnostics ───────────────────────────────────────────────────────────

    async def replay(self, event_name: Optional[str] = None) -> List[Event]:
        if event_name:
            return list(self._history.get(event_name, []))
        events: List[Event] = []
        for bucket in self._history.values():
            events.extend(bucket)
        return events

    def reset_state(self) -> None:
        self._subscribers.clear()
        self._global_subscribers.clear()
        self._history.clear()
        self._dead_letters.clear()

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "redis_enabled":    self._redis_enabled,
            "redis_channel":    self._redis_channel,
            "event_types":      list(self._subscribers.keys()),
            "global_handlers":  len(self._global_subscribers),
            "history_size":     sum(len(items) for items in self._history.values()),
            "dead_letters":     len(self._dead_letters),
        }


# ── Global singleton ──────────────────────────────────────────────────────────

event_bus = EventBus()
