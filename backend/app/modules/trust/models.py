"""
Module I — Trust, Reputation & Anti-Fraud — ORM models
Tables: user_trust_scores, fraud_flags, risk_events
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Index, Integer, Numeric, String, Text, func,
)
from app.db.database import Base


class UserTrustScore(Base):
    """Composite trust score for every user, refreshed periodically."""
    __tablename__ = "user_trust_scores"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Sub-scores (0–100 each)
    transaction_score   = Column(Float, nullable=False, default=50.0)   # wallet behaviour
    prediction_score    = Column(Float, nullable=False, default=50.0)   # prediction accuracy & consistency
    activity_score      = Column(Float, nullable=False, default=50.0)   # account age & engagement
    fraud_penalty       = Column(Float, nullable=False, default=0.0)    # deductions for active flags

    # Composite (0–100) = weighted average minus fraud_penalty
    composite_score     = Column(Float, nullable=False, default=50.0)

    # Derived risk tier: low / medium / high / critical
    risk_tier           = Column(String(16), nullable=False, default="medium")

    # Metadata
    total_flags         = Column(Integer, nullable=False, default=0)
    open_flags          = Column(Integer, nullable=False, default=0)
    last_calculated_at  = Column(DateTime(timezone=True), server_default=func.now())
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_trust_composite", "composite_score"),
        Index("idx_trust_tier",      "risk_tier"),
    )


class FraudFlag(Base):
    """A specific fraud signal raised against a user."""
    __tablename__ = "fraud_flags"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    flagged_by      = Column(String(32), nullable=False, default="system")   # system | admin | peer

    # Classification
    category        = Column(String(32), nullable=False)    # withdrawal | betting | validator | account | system
    severity        = Column(String(16), nullable=False, default="medium")  # low | medium | high | critical
    rule_code       = Column(String(64), nullable=False)    # machine-readable rule that triggered the flag
    title           = Column(String(128), nullable=False)
    detail          = Column(Text, nullable=True)

    # Review lifecycle
    status          = Column(String(20), nullable=False, default="open")   # open | reviewed | dismissed | actioned
    reviewed_by_id  = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at     = Column(DateTime(timezone=True), nullable=True)
    resolution_note = Column(Text, nullable=True)

    # Evidence context stored as JSON string
    evidence_json   = Column(Text, nullable=True)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_flag_user_id",   "user_id"),
        Index("idx_flag_status",    "status"),
        Index("idx_flag_severity",  "severity"),
        Index("idx_flag_category",  "category"),
        Index("idx_flag_created",   "created_at"),
    )


class RiskEvent(Base):
    """
    Immutable audit record for every suspicious event observed.
    Separate from FraudFlags so raw signals are never lost even when a flag is dismissed.
    """
    __tablename__ = "risk_events"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_code       = Column(String(64), nullable=False, index=True)
    score_impact    = Column(Float, nullable=False, default=0.0)   # negative = deduction
    detail          = Column(Text, nullable=True)
    evidence_json   = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_risk_event_user",    "user_id"),
        Index("idx_risk_event_rule",    "rule_code"),
        Index("idx_risk_event_created", "created_at"),
    )
