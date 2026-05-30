"""Security Layer — anti-Sybil, multi-sig, fraud detection, wallet freeze."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class SybilRisk(str, enum.Enum):
    CLEAN = "clean"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FLAGGED = "flagged"
    BANNED = "banned"


class FraudSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MultiSigStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIALLY_SIGNED = "partially_signed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"


class FreezeStatus(str, enum.Enum):
    ACTIVE = "active"
    LIFTED = "lifted"
    ESCALATED = "escalated"


class SybilProfile(Base):
    __tablename__ = "sybil_profiles"
    __table_args__ = (UniqueConstraint("user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    risk_level: Mapped[SybilRisk] = mapped_column(default=SybilRisk.CLEAN)
    anomaly_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0")
    )
    ip_cluster_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    device_fingerprints: Mapped[int] = mapped_column(default=1)
    account_age_days: Mapped[int] = mapped_column(default=0)
    prediction_velocity: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=Decimal("0")
    )
    stake_velocity: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=Decimal("0")
    )
    referral_cluster_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0")
    )
    flags: Mapped[str] = mapped_column(Text, default="")
    last_evaluated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    severity: Mapped[FraudSeverity] = mapped_column(default=FraudSeverity.INFO)
    alert_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    anomaly_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0")
    )
    resolved: Mapped[bool] = mapped_column(default=False)
    resolved_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_action: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class MultiSigOperation(Base):
    __tablename__ = "multisig_operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    payload: Mapped[str] = mapped_column(Text)
    required_signers: Mapped[int] = mapped_column(default=2)
    threshold: Mapped[int] = mapped_column(default=2)
    status: Mapped[MultiSigStatus] = mapped_column(default=MultiSigStatus.PENDING)
    proposer_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    execution_tx: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    signatures: Mapped[list["MultiSigSignature"]] = relationship(
        back_populates="operation", cascade="all, delete-orphan"
    )


class MultiSigSignature(Base):
    __tablename__ = "multisig_signatures"
    __table_args__ = (
        UniqueConstraint("operation_id", "signer_user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(
        ForeignKey("multisig_operations.id", ondelete="CASCADE")
    )
    signer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    signature_hash: Mapped[str] = mapped_column(String(66))
    approved: Mapped[bool] = mapped_column(default=True)
    signed_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    operation: Mapped["MultiSigOperation"] = relationship(back_populates="signatures")


class WalletFreeze(Base):
    __tablename__ = "wallet_freezes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[FreezeStatus] = mapped_column(default=FreezeStatus.ACTIVE)
    reason: Mapped[str] = mapped_column(Text)
    freeze_type: Mapped[str] = mapped_column(String(60), default="full")
    frozen_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 6), nullable=True
    )
    fraud_alert_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("fraud_alerts.id", ondelete="SET NULL"), nullable=True
    )
    frozen_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    lifted_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    lift_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    auto_lift_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    frozen_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    lifted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class RateLimitLedger(Base):
    __tablename__ = "rate_limit_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    endpoint: Mapped[str] = mapped_column(String(200))
    call_count: Mapped[int] = mapped_column(default=1)
    window_start: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    window_end: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    blocked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))


def _utcnow():
    return datetime.now(timezone.utc)
