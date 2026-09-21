"""AI Verification Layer — cryptographic anchoring of AI inference outputs."""
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




class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    ANCHORED = "anchored"
    DISPUTED = "disputed"
    VERIFIED = "verified"
    REJECTED = "rejected"


class AttestationKind(str, enum.Enum):
    MATCH_PREDICTION = "match_prediction"
    ACCUMULATOR = "accumulator"
    INJURY_ANALYSIS = "injury_analytics"
    MARKET_REGIME = "market_regime"
    SENTIMENT = "sentiment"
    ORACLE_CONSENSUS = "oracle_consensus"
    GOVERNANCE_AI = "governance_ai"
    AGENT_OUTPUT = "agent_output"


class AIModelAttestation(Base):
    """Registry of AI models that can produce verifiable outputs."""
    __tablename__ = "ai_model_attestations"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[str] = mapped_column(String(100), unique=True)
    model_name: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(50), default="1.0")
    capability_hash: Mapped[str] = mapped_column(String(66))
    public_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    accuracy_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    total_outputs: Mapped[int] = mapped_column(default=0)
    verified_outputs: Mapped[int] = mapped_column(default=0)
    disputed_outputs: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    registered_at: Mapped[datetime] = mapped_column(default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        default=_utcnow_naive, onupdate=_utcnow_naive
    )

    proofs: Mapped[list["InferenceProof"]] = relationship(
        back_populates="model_attestation", cascade="all, delete-orphan"
    )


class InferenceProof(Base):
    """Cryptographic proof of a single AI inference output."""
    __tablename__ = "inference_proofs"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_attestation_id: Mapped[int] = mapped_column(
        ForeignKey("ai_model_attestations.id", ondelete="CASCADE")
    )
    attestation_kind: Mapped[AttestationKind] = mapped_column()
    input_hash: Mapped[str] = mapped_column(String(66))
    output_hash: Mapped[str] = mapped_column(String(66))
    proof_hash: Mapped[str] = mapped_column(String(66), unique=True)
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    block_number: Mapped[int] = mapped_column(default=0)
    anchor_tx: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    status: Mapped[VerificationStatus] = mapped_column(
        default=VerificationStatus.PENDING
    )
    verified_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    ref_match_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    ref_prediction_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow_naive)
    anchored_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    model_attestation: Mapped["AIModelAttestation"] = relationship(
        back_populates="proofs"
    )


class VerificationDispute(Base):
    """Challenge raised against an inference proof."""
    __tablename__ = "verification_disputes"

    id: Mapped[int] = mapped_column(primary_key=True)
    proof_id: Mapped[int] = mapped_column(
        ForeignKey("inference_proofs.id", ondelete="CASCADE")
    )
    challenger_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text)
    evidence_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    resolved: Mapped[bool] = mapped_column(default=False)
    upheld: Mapped[Optional[bool]] = mapped_column(nullable=True)
    resolver_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stake_slashed: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(default=_utcnow_naive)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)