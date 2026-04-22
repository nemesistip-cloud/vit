"""Blockchain economy database models — Module C1.

All records are designed to migrate to on-chain equivalents in Phase 2
without structural changes. UUIDs are used throughout for that reason.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index,
    Integer, JSON, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Enums ──────────────────────────────────────────────────────────────

class ValidatorStatus(PyEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    SLASHED = "slashed"


class PredictionResult(PyEnum):
    PENDING = "pending"
    ACCURATE = "accurate"
    INACCURATE = "inaccurate"
    VOID = "void"


class ConsensusStatus(PyEnum):
    OPEN = "open"
    LOCKED = "locked"
    SETTLED = "settled"
    VOIDED = "voided"


class OutcomeEnum(PyEnum):
    HOME = "home"
    DRAW = "draw"
    AWAY = "away"


class StakeStatus(PyEnum):
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    REFUNDED = "refunded"


# ── Models ─────────────────────────────────────────────────────────────

class ValidatorProfile(Base):
    """Registered validator node."""
    __tablename__ = "validator_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    stake_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    trust_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.5000"))
    total_predictions: Mapped[int] = mapped_column(Integer, default=0)
    accurate_predictions: Mapped[int] = mapped_column(Integer, default=0)
    influence_score: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))

    status: Mapped[str] = mapped_column(
        String(20), default=ValidatorStatus.PENDING.value
    )

    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    predictions = relationship("ValidatorPrediction", back_populates="validator", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_validator_user_id", "user_id"),
        Index("idx_validator_status", "status"),
        Index("idx_validator_trust_score", "trust_score"),
    )


class ValidatorPrediction(Base):
    """A prediction submitted by a validator for a specific match."""
    __tablename__ = "validator_predictions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    validator_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("validator_profiles.id", ondelete="CASCADE"), nullable=False
    )
    match_id: Mapped[str] = mapped_column(String(100), nullable=False)

    p_home: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    p_draw: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    p_away: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.5"))

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    result: Mapped[str] = mapped_column(
        String(20), default=PredictionResult.PENDING.value
    )
    trust_delta: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    reward_earned: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))

    validator = relationship("ValidatorProfile", back_populates="predictions")

    __table_args__ = (
        Index("idx_val_pred_match_id", "match_id"),
        Index("idx_val_pred_validator_id", "validator_id"),
        UniqueConstraint("validator_id", "match_id", name="uq_validator_match_prediction"),
    )


class ConsensusPrediction(Base):
    """Final blended AI + validator prediction for a match."""
    __tablename__ = "consensus_predictions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    match_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    match_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    ai_p_home: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))
    ai_p_draw: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))
    ai_p_away: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))
    ai_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))
    ai_risk: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))

    validator_count: Mapped[int] = mapped_column(Integer, default=0)
    consensus_p_home: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))
    consensus_p_draw: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))
    consensus_p_away: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))

    final_p_home: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))
    final_p_draw: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))
    final_p_away: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))
    total_influence: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))

    status: Mapped[str] = mapped_column(
        String(20), default=ConsensusStatus.OPEN.value
    )
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    settlement = relationship("MatchSettlement", back_populates="consensus", uselist=False)

    __table_args__ = (
        Index("idx_consensus_match_id", "match_id"),
        Index("idx_consensus_status", "status"),
    )


class OracleResult(Base):
    """Match result submitted by an oracle source."""
    __tablename__ = "oracle_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    match_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)

    home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(String(10), nullable=False)

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    dispute_flag: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("idx_oracle_match_id", "match_id"),
        Index("idx_oracle_dispute", "dispute_flag"),
        UniqueConstraint("match_id", "source", name="uq_oracle_match_source"),
    )


class MatchSettlement(Base):
    """Settlement record after a match result is confirmed."""
    __tablename__ = "match_settlements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    match_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    consensus_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("consensus_predictions.id"), nullable=False
    )

    oracle_result: Mapped[str] = mapped_column(String(10), nullable=False)

    total_pool: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    winning_pool: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    validator_fund: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    treasury_fund: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    burn_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    ai_fund: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))

    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    consensus = relationship("ConsensusPrediction", back_populates="settlement")

    __table_args__ = (Index("idx_settlement_match_id", "match_id"),)


class UserStake(Base):
    """A user's VITCoin stake on a match outcome."""
    __tablename__ = "user_stakes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    match_id: Mapped[str] = mapped_column(String(100), nullable=False)
    prediction: Mapped[str] = mapped_column(String(10), nullable=False)
    stake_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="VITCoin")
    status: Mapped[str] = mapped_column(String(20), default=StakeStatus.ACTIVE.value)
    payout_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_stake_user_id", "user_id"),
        Index("idx_stake_match_id", "match_id"),
        Index("idx_stake_status", "status"),
    )
