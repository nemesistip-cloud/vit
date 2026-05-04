"""Storage Verification Service — content registration, proofs, challenges."""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.storage_verification.models import (
    ChallengeStatus,
    ContentHashRegistry,
    DataAvailabilityAttestation,
    StorageChallenge,
    StorageProof,
    StorageProofStatus,
)

logger = logging.getLogger(__name__)


def _sha3(data: str) -> str:
    return "0x" + hashlib.sha3_256(data.encode()).hexdigest()


async def register_content(
    db: AsyncSession,
    content_hash: str,
    content_type: str,
    ipfs_cid: str | None = None,
    arweave_id: str | None = None,
    description: str | None = None,
    size_bytes: int | None = None,
    owner_user_id: int | None = None,
    ref_type: str | None = None,
    ref_id: int | None = None,
    is_public: bool = True,
) -> ContentHashRegistry:
    existing = await db.scalar(
        select(ContentHashRegistry).where(
            ContentHashRegistry.content_hash == content_hash
        )
    )
    if existing:
        return existing

    entry = ContentHashRegistry(
        content_hash=content_hash,
        ipfs_cid=ipfs_cid,
        arweave_id=arweave_id,
        content_type=content_type,
        description=description,
        size_bytes=size_bytes,
        owner_user_id=owner_user_id,
        ref_type=ref_type,
        ref_id=ref_id,
        is_public=is_public,
        registered_at=datetime.utcnow(),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def submit_storage_proof(
    db: AsyncSession,
    content_hash: str,
    node_address: str,
    proof_data: str,
    proof_type: str = "merkle",
    prover_user_id: int | None = None,
    stake_locked: Decimal = Decimal("10"),
    validity_days: int = 30,
) -> StorageProof:
    content = await db.scalar(
        select(ContentHashRegistry).where(
            ContentHashRegistry.content_hash == content_hash
        )
    )
    if not content:
        raise ValueError("Content not registered")

    proof_hash = _sha3(f"{content_hash}:{node_address}:{proof_data}:{secrets.token_hex(8)}")

    proof = StorageProof(
        content_id=content.id,
        prover_user_id=prover_user_id,
        node_address=node_address,
        proof_type=proof_type,
        proof_data=proof_data,
        proof_hash=proof_hash,
        stake_locked=stake_locked,
        status=StorageProofStatus.ANCHORED,
        submitted_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=validity_days),
    )
    db.add(proof)

    content.replication_factor += 1
    content.last_verified_at = datetime.utcnow()

    await db.commit()
    await db.refresh(proof)
    return proof


async def issue_challenge(
    db: AsyncSession,
    proof_id: int,
    challenger_user_id: int | None = None,
    response_hours: int = 24,
) -> StorageChallenge:
    proof = await db.get(StorageProof, proof_id)
    if not proof:
        raise ValueError("Proof not found")
    if proof.status == StorageProofStatus.CHALLENGED:
        raise ValueError("Already challenged")

    nonce = secrets.token_hex(16)
    expected = _sha3(f"{proof.proof_hash}:{nonce}")

    challenge = StorageChallenge(
        proof_id=proof_id,
        challenger_user_id=challenger_user_id,
        challenge_nonce=nonce,
        expected_response_hash=expected,
        response_deadline=datetime.utcnow() + timedelta(hours=response_hours),
    )
    db.add(challenge)
    proof.status = StorageProofStatus.CHALLENGED
    await db.commit()
    await db.refresh(challenge)
    return challenge


async def respond_to_challenge(
    db: AsyncSession,
    challenge_id: int,
    response_data: str,
) -> StorageChallenge:
    challenge = await db.get(StorageChallenge, challenge_id)
    if not challenge:
        raise ValueError("Challenge not found")
    if challenge.status != ChallengeStatus.OPEN:
        raise ValueError("Challenge not open")
    if datetime.utcnow() > challenge.response_deadline:
        challenge.status = ChallengeStatus.EXPIRED
        await db.commit()
        raise ValueError("Challenge deadline passed")

    response_hash = _sha3(f"{challenge.challenge_nonce}:{response_data}")
    challenge.actual_response_hash = response_hash
    challenge.responded_at = datetime.utcnow()

    valid = response_hash == challenge.expected_response_hash
    challenge.status = (
        ChallengeStatus.RESOLVED_VALID if valid else ChallengeStatus.RESOLVED_INVALID
    )
    challenge.resolved_at = datetime.utcnow()

    proof = await db.get(StorageProof, challenge.proof_id)
    if proof:
        if valid:
            proof.status = StorageProofStatus.VERIFIED
            proof.verified_at = datetime.utcnow()
            reward = proof.stake_locked * Decimal("0.1")
            proof.reward_earned = reward
        else:
            proof.status = StorageProofStatus.FAILED
            challenge.slash_amount = proof.stake_locked

    await db.commit()
    await db.refresh(challenge)
    return challenge


async def attest_availability(
    db: AsyncSession,
    content_hash: str,
    attestor_user_id: int,
    available: bool = True,
    latency_ms: int | None = None,
) -> DataAvailabilityAttestation:
    content = await db.scalar(
        select(ContentHashRegistry).where(ContentHashRegistry.content_hash == content_hash)
    )
    if not content:
        raise ValueError("Content not registered")

    signature = _sha3(f"{content_hash}:{attestor_user_id}:{available}:{secrets.token_hex(8)}")

    existing = await db.scalar(
        select(DataAvailabilityAttestation).where(
            and_(
                DataAvailabilityAttestation.content_id == content.id,
                DataAvailabilityAttestation.attestor_user_id == attestor_user_id,
            )
        )
    )
    if existing:
        existing.available = available
        existing.latency_ms = latency_ms
        existing.signature = signature
        existing.attested_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing)
        return existing

    att = DataAvailabilityAttestation(
        content_id=content.id,
        attestor_user_id=attestor_user_id,
        available=available,
        latency_ms=latency_ms,
        signature=signature,
    )
    db.add(att)

    attestations_q = await db.execute(
        select(func.avg(DataAvailabilityAttestation.available.cast(type_=None))).where(
            DataAvailabilityAttestation.content_id == content.id
        )
    )
    avg_available = attestations_q.scalar()
    if avg_available is not None:
        content.availability_score = Decimal(str(round(float(avg_available), 4)))

    await db.commit()
    await db.refresh(att)
    return att


async def get_storage_stats(db: AsyncSession) -> dict:
    total_content = await db.scalar(select(func.count(ContentHashRegistry.id))) or 0
    total_proofs = await db.scalar(select(func.count(StorageProof.id))) or 0
    verified_proofs = await db.scalar(
        select(func.count(StorageProof.id)).where(
            StorageProof.status == StorageProofStatus.VERIFIED
        )
    ) or 0
    open_challenges = await db.scalar(
        select(func.count(StorageChallenge.id)).where(
            StorageChallenge.status == ChallengeStatus.OPEN
        )
    ) or 0
    total_bytes = await db.scalar(func.sum(ContentHashRegistry.size_bytes)) or 0
    return {
        "registered_content_items": total_content,
        "total_proofs": total_proofs,
        "verified_proofs": verified_proofs,
        "open_challenges": open_challenges,
        "total_stored_bytes": total_bytes,
        "verification_rate": (verified_proofs / total_proofs * 100) if total_proofs else 0,
    }
