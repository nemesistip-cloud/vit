"""Storage Verification Service — content registration, proofs, challenges."""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
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
    UserStorageNode,
)
from app.modules.wallet.services import WalletService

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
    is_tachyon: bool = False,
    tachyon_shards: int | None = None,
    tachyon_parity_shards: int | None = None,
    quantum_state_hash: str | None = None,
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
        is_tachyon=is_tachyon,
        tachyon_shards=tachyon_shards,
        tachyon_parity_shards=tachyon_parity_shards,
        quantum_state_hash=quantum_state_hash,
        registered_at=datetime.now(timezone.utc),
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
        submitted_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=validity_days),
    )
    db.add(proof)

    content.replication_factor += 1
    content.last_verified_at = datetime.now(timezone.utc)

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
        response_deadline=datetime.now(timezone.utc) + timedelta(hours=response_hours),
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
    if datetime.now(timezone.utc) > challenge.response_deadline:
        challenge.status = ChallengeStatus.EXPIRED
        await db.commit()
        raise ValueError("Challenge deadline passed")

    response_hash = _sha3(f"{challenge.challenge_nonce}:{response_data}")
    challenge.actual_response_hash = response_hash
    challenge.responded_at = datetime.now(timezone.utc)

    valid = response_hash == challenge.expected_response_hash
    challenge.status = (
        ChallengeStatus.RESOLVED_VALID if valid else ChallengeStatus.RESOLVED_INVALID
    )
    challenge.resolved_at = datetime.now(timezone.utc)

    proof = await db.get(StorageProof, challenge.proof_id)
    if proof:
        if valid:
            proof.status = StorageProofStatus.VERIFIED
            proof.verified_at = datetime.now(timezone.utc)
            reward = proof.stake_locked * Decimal("0.1")
            proof.reward_earned = reward

            # VESS Core: Automate VITCoin (TSC) incentive distribution
            if proof.prover_user_id:
                try:
                    ws = WalletService(db)
                    await ws.deposit_vitcoin(
                        user_id=proof.prover_user_id,
                        amount=float(reward),
                        description=f"Storage Proof Reward: {proof.proof_hash[:8]}",
                        tx_type="reward",
                        metadata={"proof_id": proof.id, "challenge_id": challenge_id}
                    )

                    # Update UserStorageNode stats if applicable
                    node_q = select(UserStorageNode).where(
                        UserStorageNode.user_id == proof.prover_user_id,
                        UserStorageNode.status == "active"
                    ).limit(1)
                    node = (await db.execute(node_q)).scalar_one_or_none()
                    if node:
                        node.tsc_earned += reward
                        node.verification_count += 1
                        node.verification_pass += 1
                        node.last_verified_at = datetime.now(timezone.utc)
                        # Calculate reliability score (EWMA style)
                        node.reliability_score = Decimal(str(min(1.0, float(node.reliability_score) * 0.95 + 0.05)))
                except Exception as e:
                    logger.error("[vess] incentive distribution failed: %s", e)
        else:
            proof.status = StorageProofStatus.FAILED
            challenge.slash_amount = proof.stake_locked

            if proof.prover_user_id:
                node_q = select(UserStorageNode).where(
                    UserStorageNode.user_id == proof.prover_user_id,
                    UserStorageNode.status == "active"
                ).limit(1)
                node = (await db.execute(node_q)).scalar_one_or_none()
                if node:
                    node.verification_count += 1
                    node.reliability_score = Decimal(str(max(0.0, float(node.reliability_score) * 0.90)))

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
        existing.attested_at = datetime.now(timezone.utc)
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


async def list_registered_content(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0
) -> list[ContentHashRegistry]:
    query = select(ContentHashRegistry).order_by(ContentHashRegistry.registered_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


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
