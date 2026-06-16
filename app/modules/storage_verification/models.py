"""Decentralized Storage Verification — content hashes, IPFS CID anchoring, proofs."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)




class StorageProofStatus(str, enum.Enum):
    PENDING = "pending"
    ANCHORED = "anchored"
    CHALLENGED = "challenged"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class ChallengeStatus(str, enum.Enum):
    OPEN = "open"
    RESPONDED = "responded"
    RESOLVED_VALID = "resolved_valid"
    RESOLVED_INVALID = "resolved_invalid"
    EXPIRED = "expired"


class ContentHashRegistry(Base):
    """Registry of content-addressable data anchored to the VIT chain."""
    __tablename__ = "content_hash_registry"
    __table_args__ = (UniqueConstraint("content_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(66))
    ipfs_cid: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    arweave_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[Optional[int]] = mapped_column(nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    ref_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    ref_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    replication_factor: Mapped[int] = mapped_column(default=1)
    availability_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("1")
    )
    is_public: Mapped[bool] = mapped_column(default=True)
    pinned: Mapped[bool] = mapped_column(default=False)
    anchor_block: Mapped[Optional[int]] = mapped_column(nullable=True)
    anchor_tx: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(default=_utcnow_naive)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Storage System Extensions
    is_tachyon: Mapped[bool] = mapped_column(default=False)
    tachyon_shards: Mapped[Optional[int]] = mapped_column(nullable=True)
    tachyon_parity_shards: Mapped[Optional[int]] = mapped_column(nullable=True)
    quantum_state_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)

    proofs: Mapped[list["StorageProof"]] = relationship(
        back_populates="content", cascade="all, delete-orphan"
    )


class StorageProof(Base):
    """Cryptographic proof that data is available at a given storage node."""
    __tablename__ = "storage_proofs"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(
        ForeignKey("content_hash_registry.id", ondelete="CASCADE")
    )
    prover_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    node_address: Mapped[str] = mapped_column(String(200))
    proof_type: Mapped[str] = mapped_column(String(60), default="merkle")
    proof_data: Mapped[str] = mapped_column(Text)
    proof_hash: Mapped[str] = mapped_column(String(66), unique=True)
    status: Mapped[StorageProofStatus] = mapped_column(
        default=StorageProofStatus.PENDING
    )
    stake_locked: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), default=Decimal("0")
    )
    reward_earned: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), default=Decimal("0")
    )
    submitted_at: Mapped[datetime] = mapped_column(default=_utcnow_naive)
    verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    content: Mapped["ContentHashRegistry"] = relationship(back_populates="proofs")
    challenge: Mapped[Optional["StorageChallenge"]] = relationship(
        back_populates="proof", uselist=False
    )


class StorageChallenge(Base):
    """Challenge issued to verify a storage proof is still valid."""
    __tablename__ = "storage_challenges"

    id: Mapped[int] = mapped_column(primary_key=True)
    proof_id: Mapped[int] = mapped_column(
        ForeignKey("storage_proofs.id", ondelete="CASCADE"), unique=True
    )
    challenger_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    challenge_nonce: Mapped[str] = mapped_column(String(66))
    expected_response_hash: Mapped[str] = mapped_column(String(66))
    actual_response_hash: Mapped[Optional[str]] = mapped_column(
        String(66), nullable=True
    )
    status: Mapped[ChallengeStatus] = mapped_column(default=ChallengeStatus.OPEN)
    slash_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), default=Decimal("0")
    )
    response_deadline: Mapped[datetime] = mapped_column(default=_utcnow_naive)
    issued_at: Mapped[datetime] = mapped_column(default=_utcnow_naive)
    responded_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    proof: Mapped["StorageProof"] = relationship(back_populates="challenge")


class DataAvailabilityAttestation(Base):
    """Multi-validator attestation of data availability."""
    __tablename__ = "data_availability_attestations"
    __table_args__ = (UniqueConstraint("content_id", "attestor_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(
        ForeignKey("content_hash_registry.id", ondelete="CASCADE")
    )
    attestor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    available: Mapped[bool] = mapped_column(default=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    signature: Mapped[str] = mapped_column(String(200))
    attested_at: Mapped[datetime] = mapped_column(default=_utcnow_naive)


class TachyonManifest(Base):
    """Persistent manifest for a Tachyon-sharded upload.

    Replaces the in-memory ``_manifests`` dict in tachyon/api/router.py so
    file metadata survives restarts and re-deploys.
    """
    __tablename__ = "tachyon_manifests"

    file_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    size_bytes: Mapped[int] = mapped_column()
    fragment_names: Mapped[dict] = mapped_column(
        __import__("sqlalchemy").JSON, nullable=False
    )
    provider_mapping: Mapped[dict] = mapped_column(
        __import__("sqlalchemy").JSON, nullable=False
    )
    owner_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        default=_utcnow_naive
    )


def _utcnow():
    return datetime.now(timezone.utc)


class NodeStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    OFFLINE = "offline"
    SUSPENDED = "suspended"


class UserStorageNode(Base):
    """
    A user-contributed cloud storage account that powers the Tachyon swarm.
    Users link their personal Google Drive / Dropbox / OneDrive and earn
    VITCoin (TSC) for every GB they contribute and every proof-of-storage
    challenge they pass.
    """
    __tablename__ = "user_storage_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(32))
    alias: Mapped[str] = mapped_column(String(128))
    config_key: Mapped[str] = mapped_column(String(256), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")

    gb_contributed: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    gb_used: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    tsc_earned: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    tsc_pending: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    reliability_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("1.0000"))
    verification_count: Mapped[int] = mapped_column(default=0)
    verification_pass: Mapped[int] = mapped_column(default=0)

    last_verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow_naive)