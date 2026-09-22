"""Stable serialization helpers for VIT protocol envelopes."""
from __future__ import annotations

from typing import Any, Mapping

from vit_protocol.proofs import canonical_bytes

SERIALIZATION_VERSION = "vit-json-1"


def serialize_envelope(value: Mapping[str, Any]) -> bytes:
    """Serialize an envelope with an explicit format marker."""
    return canonical_bytes({"serialization": SERIALIZATION_VERSION, "value": dict(value)})


def deserialize_envelope(raw: bytes) -> dict[str, Any]:
    """Decode and validate the version marker for a protocol envelope."""
    import json

    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid protocol envelope bytes") from exc
    if decoded.get("serialization") != SERIALIZATION_VERSION or not isinstance(decoded.get("value"), dict):
        raise ValueError("unsupported protocol envelope serialization")
    return decoded["value"]
