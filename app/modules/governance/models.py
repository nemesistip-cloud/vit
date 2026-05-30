# app/modules/governance/models.py
"""Governance Layer database models — Module M."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Proposal(Base):
    """M1 — A governance proposal."""
    __tablename__ = "gov_proposals"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    proposer_id     : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title           : Mapped[str]      = mapped_column(String(256), nullable=False)
    description     : Mapped[str]      = mapped_column(Text, nullable=False)
    category        : Mapped[str]      = mapped_column(String(64), default="general")
    # category: fee_change | parameter_update | feature_approval | general

    # Parameter change payload (optional — JSON encoded as string)
    change_payload  : Mapped[str]      = mapped_column(Text, nullable=True)

    # State machine: draft → active → passed | rejected | cancelled | executed
    status          : Mapped[str]      = mapped_column(String(20), default="draft")

    # Voting period (epoch timestamps)
    voting_starts_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    voting_ends_at   : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timelock (seconds before execution after passing)
    timelock_seconds : Mapped[int]     = mapped_column(Integer, default=86400)   # 24 h default
    executed_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_note   : Mapped[str]     = mapped_column(Text, nullable=True)

    # Vote tallies (cached)
    votes_for       : Mapped[float]    = mapped_column(Float, default=0.0)
    votes_against   : Mapped[float]    = mapped_column(Float, default=0.0)
    votes_abstain   : Mapped[float]    = mapped_column(Float, default=0.0)
    quorum_required : Mapped[float]    = mapped_column(Float, default=1000.0)   # voting power threshold

    created_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    proposer = relationship("User", foreign_keys=[proposer_id])
    votes    = relationship("Vote", back_populates="proposal", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_gov_proposal_status",      "status"),
        Index("idx_gov_proposal_proposer_id", "proposer_id"),
    )

    @property
    def total_votes(self) -> float:
        return (self.votes_for or 0.0) + (self.votes_against or 0.0) + (self.votes_abstain or 0.0)

    @property
    def approval_pct(self) -> float:
        total = self.votes_for + self.votes_against
        return round(self.votes_for / total * 100, 2) if total > 0 else 0.0


class Vote(Base):
    """M2 — One vote per user per proposal. Vote power = stake × trust_score."""
    __tablename__ = "gov_votes"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    proposal_id     : Mapped[int]      = mapped_column(Integer, ForeignKey("gov_proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    voter_id        : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    choice          : Mapped[str]      = mapped_column(String(10), nullable=False)   # for | against | abstain
    voting_power    : Mapped[float]    = mapped_column(Float, nullable=False)
    reason          : Mapped[str]      = mapped_column(Text, nullable=True)

    voted_at        : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    proposal = relationship("Proposal", back_populates="votes")
    voter    = relationship("User", foreign_keys=[voter_id])

    __table_args__ = (
        UniqueConstraint("proposal_id", "voter_id", name="uq_gov_vote_proposal_voter"),
        Index("idx_gov_vote_proposal_id", "proposal_id"),
        Index("idx_gov_vote_voter_id",    "voter_id"),
    )


class GovernanceConfig(Base):
    """M3 — Protocol parameters managed by governance."""
    __tablename__ = "gov_configs"

    id          : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    key         : Mapped[str]      = mapped_column(String(64), unique=True, nullable=False)
    value       : Mapped[str]      = mapped_column(Text, nullable=False)
    data_type   : Mapped[str]      = mapped_column(String(16), default="string")   # string | int | float | bool
    description : Mapped[str]      = mapped_column(Text, nullable=True)
    updated_by  : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at  : Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    created_at  : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
