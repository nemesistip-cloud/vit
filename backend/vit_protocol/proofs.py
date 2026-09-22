"""Canonical off-chain proof envelopes for VIT data and AI outputs.

This module deliberately has no database, FastAPI, chain, or cryptography
framework dependency. It defines the bytes that future protocol attestations
can commit to VIT Chain without putting large payloads on-chain.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

PROOF_VERSION = "1"
REQUIRED_FIELDS = (
    "proof_id",
    "proof_type",
    "object_id",
    "object_version",
    "data_hash",
    "timestamp",
    "signer",
    "signature",
)


class ProofEnvelopeError(ValueError):
    """Raised when a proof envelope is structurally or cryptographically invalid."""


def canonical_bytes(value: Any) -> bytes:
    """Serialize JSON-compatible data deterministically for hashing/signing."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProofEnvelopeError("value is not canonical JSON data") from exc


def sha256_hash(value: Any) -> str:
    """Return a versioned SHA-256 content hash."""
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def _proof_identity_fields(envelope: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: envelope[key]
        for key in envelope
        if key not in {"proof_id", "signature"}
    }


def build_proof_envelope(
    *,
    proof_type: str,
    object_id: str,
    object_version: str,
    timestamp: str,
    signer: str,
    payload: Any,
    signature: str = "",
    evidence_reference: str | None = None,
    model_id: str | None = None,
    model_version: str | None = None,
    result: Any | None = None,
    chain_reference: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a canonical proof envelope; signing is intentionally external."""
    if not proof_type or not object_id or not object_version or not timestamp or not signer:
        raise ProofEnvelopeError("proof_type, object_id, version, timestamp, and signer are required")

    envelope: dict[str, Any] = {
        "proof_version": PROOF_VERSION,
        "proof_type": proof_type,
        "object_id": object_id,
        "object_version": object_version,
        "data_hash": sha256_hash(payload),
        "timestamp": timestamp,
        "signer": signer,
        "signature": signature,
    }
    optional = {
        "evidence_reference": evidence_reference,
        "model_id": model_id,
        "model_version": model_version,
        "result_hash": sha256_hash(result) if result is not None else None,
        "chain_reference": dict(chain_reference) if chain_reference else None,
    }
    envelope.update({key: value for key, value in optional.items() if value is not None})
    envelope["proof_id"] = "proof:" + hashlib.sha256(canonical_bytes(_proof_identity_fields(envelope))).hexdigest()
    return envelope


def verify_proof_envelope(envelope: Mapping[str, Any], payload: Any | None = None) -> dict[str, Any]:
    """Verify envelope structure and, when supplied, the referenced payload hash."""
    missing = [field for field in REQUIRED_FIELDS if field not in envelope]
    if missing:
        raise ProofEnvelopeError(f"missing proof fields: {', '.join(missing)}")
    if envelope.get("proof_version") != PROOF_VERSION:
        raise ProofEnvelopeError("unsupported proof version")
    if payload is not None and envelope["data_hash"] != sha256_hash(payload):
        raise ProofEnvelopeError("payload hash does not match proof envelope")

    expected_id = "proof:" + hashlib.sha256(canonical_bytes(_proof_identity_fields(envelope))).hexdigest()
    if envelope["proof_id"] != expected_id:
        raise ProofEnvelopeError("proof_id does not match canonical envelope")

    return {
        "valid": True,
        "payload_verified": payload is not None,
        "signature_status": "present" if bool(envelope.get("signature")) else "unsigned",
        "proof_id": envelope["proof_id"],
    }
