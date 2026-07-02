import asyncio
import logging
from typing import Dict, List, Callable, Any, Awaitable, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

@dataclass
class Event:
    name: str
    payload: Dict[str, Any]
    sender: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class EventBus:
    """Centralized asynchronous event bus for the VIT Platform."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._subscribers = {}
            cls._instance._global_subscribers = []
        return cls._instance

    def subscribe(self, event_name: str, handler: Callable[[Event], Awaitable[None]]):
        """Subscribe to a specific event."""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(handler)
        logger.debug(f"[event_bus] Subscribed handler to event: {event_name}")

    def subscribe_all(self, handler: Callable[[Event], Awaitable[None]]):
        """Subscribe to all events."""
        self._global_subscribers.append(handler)
        logger.debug("[event_bus] Subscribed global handler")

    async def publish(self, event_name: str, payload: Dict[str, Any], sender: str = "system"):
        """Publish an event to all subscribers."""
        event = Event(name=event_name, payload=payload, sender=sender)

        handlers = self._subscribers.get(event_name, []).copy()
        handlers.extend(self._global_subscribers)

        if not handlers:
            logger.debug(f"[event_bus] No subscribers for event: {event_name}")
            return

        tasks = [self._safe_execute(handler, event) for handler in handlers]
        await asyncio.gather(*tasks)

    async def _safe_execute(self, handler: Callable[[Event], Awaitable[None]], event: Event):
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"[event_bus] Error in event handler for {event.name}: {e}")

# Global Instance
event_bus = EventBus()
