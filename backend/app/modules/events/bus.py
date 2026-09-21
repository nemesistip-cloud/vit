from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Type, TypeVar

EventT = TypeVar("EventT", bound="Event")


@dataclass(slots=True, kw_only=True)
class Event:
    event_id: Optional[str] = None


@dataclass(slots=True, kw_only=True)
class UserRegistered(Event):
    user_id: str
    email: str


@dataclass(slots=True, kw_only=True)
class UserLoggedIn(Event):
    user_id: str
    session_id: str


@dataclass(slots=True, kw_only=True)
class WalletCreated(Event):
    user_id: str
    wallet_id: str


@dataclass(slots=True, kw_only=True)
class StorageInitialized(Event):
    user_id: str
    storage_id: str


@dataclass(slots=True, kw_only=True)
class AIProfileCreated(Event):
    user_id: str
    profile_id: str


@dataclass(slots=True, kw_only=True)
class NotificationCreated(Event):
    user_id: str
    notification_id: str


EventHandler = Callable[[Event], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: Dict[Type[Event], List[EventHandler]] = {}

    def subscribe(self, event_type: Type[EventT], handler: Callable[[EventT], None]) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: EventT) -> None:
        for handler in self._handlers.get(type(event), []):
            handler(event)

    def clear(self) -> None:
        self._handlers.clear()
