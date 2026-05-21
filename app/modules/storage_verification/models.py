"""Decentralized Storage Verification — content hashes, IPFS CID anchoring, proofs."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


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
    registered_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

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
    submitted_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
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
    response_deadline: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    issued_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
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
    attested_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))


def _utcnow():
    return datetime.now(timezone.utc)
