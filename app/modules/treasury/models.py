"""Treasury System — governance-controlled multi-pool VIT treasury."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import JSON, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class PoolType(str, enum.Enum):
    VALIDATOR_REWARDS = "validator_rewards"
    AI_INFRASTRUCTURE = "ai_infrastructure"
    ECOSYSTEM_GRANTS = "ecosystem_grants"
    RESERVE = "reserve"
    ORACLE_INCENTIVES = "oracle_incentives"
    PREDICTION_LIQUIDITY = "prediction_liquidity"
    BUG_BOUNTY = "bug_bounty"
    TEAM_VESTING = "team_vesting"
    COMMUNITY_POOL = "community_pool"


class ProposalStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class AllocationStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    RELEASED = "released"
    CLAWED_BACK = "clawed_back"


class TreasuryPool(Base):
    __tablename__ = "treasury_pools"

    id: Mapped[int] = mapped_column(primary_key=True)
    pool_type: Mapped[PoolType] = mapped_column(unique=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 6), default=Decimal("0"))
    total_deposited: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), default=Decimal("0")
    )
    total_spent: Mapped[Decimal] = mapped_column(Numeric(20, 6), default=Decimal("0"))
    allocation_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0")
    )
    auto_refill: Mapped[bool] = mapped_column(default=False)
    refill_threshold: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), default=Decimal("0")
    )
    refill_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), default=Decimal("0")
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    allocations: Mapped[list["TreasuryAllocation"]] = relationship(
        back_populates="pool", cascade="all, delete-orphan"
    )


class GrantProposal(Base):
    __tablename__ = "grant_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    proposer_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    pool_type: Mapped[PoolType] = mapped_column()
    requested_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    approved_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 6), nullable=True
    )
    recipient_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recipient_address: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    status: Mapped[ProposalStatus] = mapped_column(default=ProposalStatus.DRAFT)
    milestones: Mapped[dict] = mapped_column(JSON, default=dict)
    votes_for: Mapped[int] = mapped_column(default=0)
    votes_against: Mapped[int] = mapped_column(default=0)
    governance_proposal_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    approved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    allocations: Mapped[list["TreasuryAllocation"]] = relationship(
        back_populates="grant", cascade="all, delete-orphan"
    )


class TreasuryAllocation(Base):
    __tablename__ = "treasury_allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    pool_id: Mapped[int] = mapped_column(
        ForeignKey("treasury_pools.id", ondelete="CASCADE")
    )
    grant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("grant_proposals.id", ondelete="SET NULL"), nullable=True
    )
    recipient_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    reason: Mapped[str] = mapped_column(String(255))
    status: Mapped[AllocationStatus] = mapped_column(
        default=AllocationStatus.SCHEDULED
    )
    tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    released_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    pool: Mapped["TreasuryPool"] = relationship(back_populates="allocations")
    grant: Mapped[Optional["GrantProposal"]] = relationship(
        back_populates="allocations"
    )


class TreasuryDeposit(Base):
    __tablename__ = "treasury_deposits"

    id: Mapped[int] = mapped_column(primary_key=True)
    pool_type: Mapped[PoolType] = mapped_column()
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    source: Mapped[str] = mapped_column(String(100))
    depositor_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deposited_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)
