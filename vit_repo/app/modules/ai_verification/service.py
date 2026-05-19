"""AI Verification Service — hash anchoring, proof lifecycle, dispute resolution."""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_verification.models import (
    AIModelAttestation,
    AttestationKind,
    InferenceProof,
    VerificationDispute,
    VerificationStatus,
)

logger = logging.getLogger(__name__)

BUILTIN_MODELS = [
    {"model_id": "gemini-2.0-flash", "name": "Google Gemini 2.0 Flash", "provider": "google", "version": "2.0"},
    {"model_id": "gpt-4o", "name": "OpenAI GPT-4o", "provider": "openai", "version": "4o"},
    {"model_id": "grok-2", "name": "xAI Grok-2", "provider": "xai", "version": "2.0"},
    {"model_id": "vit-prediction-v3", "name": "VIT Match Prediction Model v3", "provider": "vit", "version": "3.0"},
    {"model_id": "vit-oracle-consensus", "name": "VIT Oracle Consensus Engine", "provider": "vit", "version": "2.1"},
]


def _hash_input(data: Any) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str)
    return "0x" + hashlib.sha3_256(serialized.encode()).hexdigest()


def _hash_output(data: Any) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str)
    return "0x" + hashlib.sha3_256(serialized.encode()).hexdigest()


def _compute_proof_hash(input_hash: str, output_hash: str, model_id: str, ts: str) -> str:
    raw = f"{input_hash}:{output_hash}:{model_id}:{ts}:{secrets.token_hex(8)}"
    return "0x" + hashlib.sha3_256(raw.encode()).hexdigest()


async def bootstrap_model_registry(db: AsyncSession) -> int:
    created = 0
    for m in BUILTIN_MODELS:
        existing = await db.scalar(
            select(AIModelAttestation).where(AIModelAttestation.model_id == m["model_id"])
        )
        if not existing:
            cap_hash = "0x" + hashlib.sha3_256(
                f"{m['model_id']}:{m['version']}".encode()
            ).hexdigest()
            attestation = AIModelAttestation(
                model_id=m["model_id"],
                model_name=m["name"],
                provider=m["provider"],
                version=m["version"],
                capability_hash=cap_hash,
                is_active=True,
            )
            db.add(attestation)
            created += 1
    if created:
        await db.commit()
    return created


async def anchor_inference(
    db: AsyncSession,
    model_id: str,
    attestation_kind: AttestationKind,
    input_data: Any,
    output_data: Any,
    confidence: float | None = None,
    ref_match_id: int | None = None,
    ref_prediction_id: int | None = None,
    input_summary: str | None = None,
    output_summary: str | None = None,
) -> InferenceProof:
    model = await db.scalar(
        select(AIModelAttestation).where(AIModelAttestation.model_id == model_id)
    )
    if not model:
        raise ValueError(f"Model {model_id} not registered")

    ts = datetime.now(timezone.utc).isoformat()
    input_hash = _hash_input(input_data)
    output_hash = _hash_output(output_data)
    proof_hash = _compute_proof_hash(input_hash, output_hash, model_id, ts)

    proof = InferenceProof(
        model_attestation_id=model.id,
        attestation_kind=attestation_kind,
        input_hash=input_hash,
        output_hash=output_hash,
        proof_hash=proof_hash,
        confidence=Decimal(str(confidence)) if confidence is not None else None,
        ref_match_id=ref_match_id,
        ref_prediction_id=ref_prediction_id,
        input_summary=input_summary,
        output_summary=output_summary,
        status=VerificationStatus.ANCHORED,
        anchored_at=datetime.now(timezone.utc),
        block_number=0,
    )
    db.add(proof)

    model.total_outputs += 1
    await db.commit()
    await db.refresh(proof)
    return proof


async def verify_proof(
    db: AsyncSession,
    proof_hash: str,
    verifier_user_id: int | None = None,
) -> InferenceProof:
    proof = await db.scalar(
        select(InferenceProof).where(InferenceProof.proof_hash == proof_hash)
    )
    if not proof:
        raise ValueError("Proof not found")

    proof.status = VerificationStatus.VERIFIED
    proof.verified_by_user_id = verifier_user_id
    proof.verified_at = datetime.now(timezone.utc)

    model = await db.get(AIModelAttestation, proof.model_attestation_id)
    if model:
        model.verified_outputs += 1

    await db.commit()
    await db.refresh(proof)
    return proof


async def raise_dispute(
    db: AsyncSession,
    proof_hash: str,
    reason: str,
    challenger_user_id: int | None = None,
    evidence_hash: str | None = None,
) -> VerificationDispute:
    proof = await db.scalar(
        select(InferenceProof).where(InferenceProof.proof_hash == proof_hash)
    )
    if not proof:
        raise ValueError("Proof not found")

    proof.status = VerificationStatus.DISPUTED
    model = await db.get(AIModelAttestation, proof.model_attestation_id)
    if model:
        model.disputed_outputs += 1

    dispute = VerificationDispute(
        proof_id=proof.id,
        challenger_user_id=challenger_user_id,
        reason=reason,
        evidence_hash=evidence_hash,
    )
    db.add(dispute)
    await db.commit()
    await db.refresh(dispute)
    return dispute


async def resolve_dispute(
    db: AsyncSession,
    dispute_id: int,
    upheld: bool,
    resolver_user_id: int,
    resolution_notes: str | None = None,
    slash_amount: Decimal = Decimal("0"),
) -> VerificationDispute:
    dispute = await db.get(VerificationDispute, dispute_id)
    if not dispute:
        raise ValueError("Dispute not found")

    dispute.resolved = True
    dispute.upheld = upheld
    dispute.resolver_user_id = resolver_user_id
    dispute.resolution_notes = resolution_notes
    dispute.stake_slashed = slash_amount
    dispute.resolved_at = datetime.now(timezone.utc)

    proof = await db.get(InferenceProof, dispute.proof_id)
    if proof:
        proof.status = VerificationStatus.REJECTED if upheld else VerificationStatus.VERIFIED

    await db.commit()
    await db.refresh(dispute)
    return dispute


async def get_verification_stats(db: AsyncSession) -> dict:
    total = await db.scalar(select(func.count(InferenceProof.id))) or 0
    by_status = await db.execute(
        select(InferenceProof.status, func.count(InferenceProof.id))
        .group_by(InferenceProof.status)
    )
    by_kind = await db.execute(
        select(InferenceProof.attestation_kind, func.count(InferenceProof.id))
        .group_by(InferenceProof.attestation_kind)
    )
    total_models = await db.scalar(
        select(func.count(AIModelAttestation.id))
        .where(AIModelAttestation.is_active.is_(True))
    ) or 0
    return {
        "total_proofs": total,
        "active_models": total_models,
        "by_status": {r[0].value: r[1] for r in by_status.all()},
        "by_kind": {r[0].value: r[1] for r in by_kind.all()},
    }
