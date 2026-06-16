"""AI Agent Registry — formal registration, staking, reputation, proof anchoring."""
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




class AgentStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"
    SLASHED = "slashed"


class AgentCapability(str, enum.Enum):
    PREDICTION = "prediction"
    ORACLE = "oracle"
    SENTIMENT = "sentiment"
    RISK_ANALYSIS = "risk_analytics"
    GOVERNANCE = "governance"
    TRADING = "trading"
    DATA_PROCESSING = "data_processing"
    VERIFICATION = "verification"
    GENERAL = "general"


class CredentialStatus(str, enum.Enum):
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AIAgentRegistration(Base):
    __tablename__ = "ai_agent_registrations"
    __table_args__ = (UniqueConstraint("agent_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[AgentStatus] = mapped_column(default=AgentStatus.PENDING)
    capabilities: Mapped[str] = mapped_column(Text, default="[]")
    did_identifier: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, unique=True
    )
    public_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    endpoint_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    stake_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), default=Decimal("0")
    )
    reputation_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=Decimal("50")
    )
    accuracy_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0")
    )
    total_tasks: Mapped[int] = mapped_column(default=0)
    successful_tasks: Mapped[int] = mapped_column(default=0)
    failed_tasks: Mapped[int] = mapped_column(default=0)
    total_earned_vit: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), default=Decimal("0")
    )
    total_slashed_vit: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), default=Decimal("0")
    )
    version: Mapped[str] = mapped_column(String(30), default="1.0.0")
    is_builtin: Mapped[bool] = mapped_column(default=False)
    registered_at: Mapped[datetime] = mapped_column(default=_utcnow_naive.replace(tzinfo=None))
    last_active_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        default=_utcnow_naive.replace(tzinfo=None), onupdate=_utcnow_naive.replace(tzinfo=None)
    )

    performance_records: Mapped[list["AgentPerformanceRecord"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
    credentials: Mapped[list["AgentCredential"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
    payment_routes: Mapped[list["AgentPaymentRoute"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


class AgentPerformanceRecord(Base):
    __tablename__ = "agent_performance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("ai_agent_registrations.id", ondelete="CASCADE")
    )
    task_type: Mapped[str] = mapped_column(String(100))
    task_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    success: Mapped[bool] = mapped_column(default=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    accuracy: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    vit_earned: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), default=Decimal("0")
    )
    proof_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(default=_utcnow_naive.replace(tzinfo=None))

    agent: Mapped["AIAgentRegistration"] = relationship(
        back_populates="performance_records"
    )


class AgentCredential(Base):
    __tablename__ = "agent_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("ai_agent_registrations.id", ondelete="CASCADE")
    )
    credential_type: Mapped[str] = mapped_column(String(100))
    credential_hash: Mapped[str] = mapped_column(String(66))
    issued_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[CredentialStatus] = mapped_column(default=CredentialStatus.VALID)
    issued_at: Mapped[datetime] = mapped_column(default=_utcnow_naive.replace(tzinfo=None))
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    agent: Mapped["AIAgentRegistration"] = relationship(back_populates="credentials")


class AgentPaymentRoute(Base):
    __tablename__ = "agent_payment_routes"
    __table_args__ = (UniqueConstraint("agent_id", "route_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("ai_agent_registrations.id", ondelete="CASCADE")
    )
    route_type: Mapped[str] = mapped_column(String(60))
    recipient_address: Mapped[str] = mapped_column(String(200))
    split_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("100"))
    is_active: Mapped[bool] = mapped_column(default=True)
    total_routed: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(default=_utcnow_naive.replace(tzinfo=None))

    agent: Mapped["AIAgentRegistration"] = relationship(
        back_populates="payment_routes"
    )


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)