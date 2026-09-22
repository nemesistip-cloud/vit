"""Canonical VIT event envelopes for protocol, service, and app events."""
from __future__ import annotations

from typing import Any, Mapping
from uuid import uuid4

from vit_protocol.proofs import sha256_hash

EVENT_TYPES = {
    "BlockFinalized",
    "PaymentSubmitted",
    "PaymentConfirmed",
    "ValidatorJoined",
    "ValidatorExited",
    "StorageUploaded",
    "StorageVerified",
    "AIInferenceCompleted",
    "PredictionCreated",
    "ApplicationRegistered",
    "DeveloperRegistered",
}


class EventEnvelopeError(ValueError):
    """Raised when an event envelope is invalid."""


def build_event(
    *,
    event_type: str,
    source: str,
    payload: Any,
    timestamp: str,
    block_reference: Mapping[str, Any] | None = None,
    signature: str = "",
    event_id: str | None = None,
) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise EventEnvelopeError(f"unsupported event type: {event_type}")
    if not source or not timestamp:
        raise EventEnvelopeError("source and timestamp are required")
    return {
        "event_id": event_id or f"evt:{uuid4()}",
        "event_type": event_type,
        "source": source,
        "timestamp": timestamp,
        "block_reference": dict(block_reference) if block_reference else None,
        "payload_hash": sha256_hash(payload),
        "signature": signature,
        "delivery": {"mode": "at_least_once", "cursor": None},
    }


def verify_event_payload(event: Mapping[str, Any], payload: Any) -> bool:
    if not event.get("event_id") or not event.get("event_type"):
        raise EventEnvelopeError("event_id and event_type are required")
    if event["event_type"] not in EVENT_TYPES:
        raise EventEnvelopeError("unsupported event type")
    return event.get("payload_hash") == sha256_hash(payload)
