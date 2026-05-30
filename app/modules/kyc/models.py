"""KYC (Know Your Customer) models — offline rule-based verification.

No external API keys required. All validation is done locally using
deterministic rule engines.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer,
    JSON, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class KYCStatus(str, enum.Enum):
    NONE          = "none"
    PENDING       = "pending"
    AUTO_APPROVED = "auto_approved"
    MANUAL_REVIEW = "manual_review"
    APPROVED      = "approved"
    REJECTED      = "rejected"
    EXPIRED       = "expired"


class KYCDocumentType(str, enum.Enum):
    NATIONAL_ID      = "national_id"
    PASSPORT         = "passport"
    DRIVERS_LICENSE  = "drivers_license"
    RESIDENT_PERMIT  = "resident_permit"
    VOTER_CARD       = "voter_card"
    BVN              = "bvn"          # Nigerian Bank Verification Number
    NIN              = "nin"          # Nigerian National ID Number


class KYCRiskLevel(str, enum.Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class KYCSubmission(Base):
    """Full KYC lifecycle record — one active record per user."""
    __tablename__ = "kyc_submissions"
    __table_args__ = (
        Index("idx_kyc_user_id", "user_id"),
        Index("idx_kyc_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Identity data (user-submitted)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[str] = mapped_column(String(20), nullable=False)  # YYYY-MM-DD
    nationality: Mapped[str] = mapped_column(String(80), nullable=False)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    document_number: Mapped[str] = mapped_column(String(60), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Offline rule-engine output
    status: Mapped[KYCStatus] = mapped_column(default=KYCStatus.PENDING)
    risk_level: Mapped[KYCRiskLevel] = mapped_column(default=KYCRiskLevel.LOW)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)   # 0-100
    rule_checks: Mapped[dict] = mapped_column(JSON, default=dict) # pass/fail per rule
    risk_flags: Mapped[list] = mapped_column(JSON, default=list)  # list of flag strings

    # Reviewer / admin fields
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # Selfie / liveness (base64 thumbnail stored in JSON for portability)
    selfie_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class KYCAuditEvent(Base):
    """Append-only audit trail for every KYC status change."""
    __tablename__ = "kyc_audit_events"
    __table_args__ = (Index("idx_kyc_audit_submission", "submission_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("kyc_submissions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)  # submitted, approved, etc.
    from_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
