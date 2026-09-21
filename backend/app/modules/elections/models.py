# app/modules/elections/models.py
"""Electoral & Policy Simulator — database models (TRACK-015)."""

import uuid
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, Float, ForeignKey,
    Integer, JSON, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base

import enum


class ElectionType(str, enum.Enum):
    presidential  = "presidential"
    parliamentary = "parliamentary"
    referendum    = "referendum"
    local         = "local"
    senate        = "senate"


class ElectionStatus(str, enum.Enum):
    upcoming   = "upcoming"
    active     = "active"
    concluded  = "concluded"


class PolicyCategory(str, enum.Enum):
    fiscal      = "fiscal"
    social      = "social"
    trade       = "trade"
    security    = "security"
    environment = "environment"
    healthcare  = "healthcare"
    education   = "education"


class PolicyStatus(str, enum.Enum):
    draft    = "draft"
    proposed = "proposed"
    adopted  = "adopted"
    rejected = "rejected"


# ── Legacy models kept for backward compatibility ────────────────────────────

def _utcnow_naive():
    return datetime.utcnow()


class ElectionEvent(Base):
    __tablename__ = "election_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[str] = mapped_column(String(36), ForeignKey("markets.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(100))
    date: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(50), default="upcoming")
    candidates: Mapped[dict] = mapped_column(JSON)
    sentiment_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    market = relationship("app.db.models.Market")


class PollingData(Base):
    __tablename__ = "polling_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    election_id: Mapped[int] = mapped_column(index=True)
    source: Mapped[str] = mapped_column(String(100))
    data: Mapped[dict] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)


# ── New TRACK-015 models ─────────────────────────────────────────────────────

class Election(Base):
    """A real-world electoral contest."""
    __tablename__ = "elections"

    id            = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    title         = Column(String(255), nullable=False)
    country       = Column(String(3), nullable=False, index=True)
    election_type = Column(
        Enum(ElectionType, name="election_type_enum"),
        nullable=False,
        index=True,
    )
    election_date = Column(Date, nullable=False)
    status        = Column(
        Enum(ElectionStatus, name="election_status_enum"),
        nullable=False,
        default=ElectionStatus.upcoming,
        index=True,
    )
    description   = Column(Text, nullable=True)
    total_seats   = Column(Integer, nullable=True)
    metadata_     = Column("metadata", JSON, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    candidates  = relationship("Candidate",         back_populates="election", cascade="all, delete-orphan")
    polls       = relationship("ElectionPoll",       back_populates="election", cascade="all, delete-orphan")
    predictions = relationship("ElectionPrediction", back_populates="election", cascade="all, delete-orphan")


class Candidate(Base):
    """A candidate in an Election."""
    __tablename__ = "candidates"

    id            = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    election_id   = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, index=True)
    name          = Column(String(255), nullable=False)
    party         = Column(String(255), nullable=False)
    position      = Column(String(255), nullable=True)
    bio           = Column(Text, nullable=True)
    polling_avg   = Column(Float, nullable=False, default=0.0)
    win_probability = Column(Float, nullable=False, default=0.0)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    election    = relationship("Election",           back_populates="candidates")
    predictions = relationship("ElectionPrediction", back_populates="candidate", cascade="all, delete-orphan")


class ElectionPoll(Base):
    """A single poll result for an Election."""
    __tablename__ = "election_polls"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    election_id     = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, index=True)
    pollster        = Column(String(255), nullable=False)
    conducted_date  = Column(Date, nullable=False)
    sample_size     = Column(Integer, nullable=False)
    methodology     = Column(String(255), nullable=True)
    margin_of_error = Column(Float, nullable=False, default=3.0)
    results         = Column(JSON, nullable=False)   # list of {candidate_id, percentage}
    weight          = Column(Float, nullable=False, default=1.0)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    election = relationship("Election", back_populates="polls")


class ElectionPrediction(Base):
    """A user-submitted prediction for an Election."""
    __tablename__ = "election_predictions"

    id                = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    election_id       = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id           = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id      = Column(String(36), ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True)
    predicted_outcome = Column(JSON, nullable=False)
    reasoning         = Column(Text, nullable=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    election  = relationship("Election",  back_populates="predictions")
    candidate = relationship("Candidate", back_populates="predictions")
    user      = relationship("app.db.models.User")


class PolicyProposal(Base):
    """A real-world policy proposal with impact scoring."""
    __tablename__ = "policy_proposals"

    id           = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    title        = Column(String(255), nullable=False)
    jurisdiction = Column(String(255), nullable=False)
    category     = Column(
        Enum(PolicyCategory, name="policy_category_enum"),
        nullable=False,
        index=True,
    )
    description  = Column(Text, nullable=False)
    sponsor      = Column(String(255), nullable=False)
    status       = Column(
        Enum(PolicyStatus, name="policy_status_enum"),
        nullable=False,
        default=PolicyStatus.draft,
        index=True,
    )
    impact_scores = Column(JSON, nullable=True)   # dict[domain, float]
    metadata_     = Column("metadata", JSON, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
