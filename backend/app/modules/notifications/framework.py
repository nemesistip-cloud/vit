from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


class DeliveryChannel(Protocol):
    async def send(self, recipient: str, title: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        ...


@dataclass(slots=True)
class NotificationEnvelope:
    channel: str
    recipient: str
    title: str
    body: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class InAppChannel:
    async def send(self, recipient: str, title: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        return None


class EmailChannel:
    async def send(self, recipient: str, title: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        return None


class PushChannel:
    async def send(self, recipient: str, title: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        return None


class NotificationService:
    """Unified notification framework with in-app, email, and push abstractions."""

    def __init__(self) -> None:
        self._channels: Dict[str, DeliveryChannel] = {}

    def register_channel(self, channel_name: str, channel: DeliveryChannel) -> None:
        self._channels[channel_name] = channel

    async def send(self, envelope: NotificationEnvelope) -> None:
        channel = self._channels.get(envelope.channel)
        if channel is None:
            raise KeyError(f"Unknown channel: {envelope.channel}")
        await channel.send(envelope.recipient, envelope.title, envelope.body, envelope.metadata)
