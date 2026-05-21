"""Smart Contract Engine — on-chain rule-based contract system."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import JSON, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ContractStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"
    UPGRADING = "upgrading"


class CallStatus(str, enum.Enum):
    SUCCESS = "success"
    REVERTED = "reverted"
    OUT_OF_GAS = "out_of_gas"
    INVALID = "invalid"


class SmartContract(Base):
    __tablename__ = "smart_contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    address: Mapped[str] = mapped_column(String(66), unique=True)
    deployer_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ContractStatus] = mapped_column(default=ContractStatus.ACTIVE)
    abi: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    rules: Mapped[dict] = mapped_column(JSON, default=dict)
    gas_limit: Mapped[int] = mapped_column(default=1_000_000)
    total_calls: Mapped[int] = mapped_column(default=0)
    total_gas_used: Mapped[int] = mapped_column(default=0)
    vit_locked: Mapped[Decimal] = mapped_column(Numeric(20, 6), default=Decimal("0"))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_builtin: Mapped[bool] = mapped_column(default=False)
    deployed_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    calls: Mapped[list["ContractCall"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan"
    )
    events: Mapped[list["ContractEvent"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan"
    )


class ContractCall(Base):
    __tablename__ = "contract_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(
        ForeignKey("smart_contracts.id", ondelete="CASCADE")
    )
    caller_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    method: Mapped[str] = mapped_column(String(120))
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[CallStatus] = mapped_column(default=CallStatus.SUCCESS)
    gas_used: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tx_hash: Mapped[str] = mapped_column(String(66), unique=True)
    block_number: Mapped[int] = mapped_column(default=0)
    called_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    contract: Mapped["SmartContract"] = relationship(back_populates="calls")


class ContractEvent(Base):
    __tablename__ = "contract_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(
        ForeignKey("smart_contracts.id", ondelete="CASCADE")
    )
    call_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contract_calls.id", ondelete="SET NULL"), nullable=True
    )
    event_name: Mapped[str] = mapped_column(String(120))
    topic: Mapped[str] = mapped_column(String(66))
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    log_index: Mapped[int] = mapped_column(default=0)
    block_number: Mapped[int] = mapped_column(default=0)
    emitted_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    contract: Mapped["SmartContract"] = relationship(back_populates="events")


class ContractUpgrade(Base):
    __tablename__ = "contract_upgrades"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(
        ForeignKey("smart_contracts.id", ondelete="CASCADE")
    )
    from_version: Mapped[str] = mapped_column(String(20))
    to_version: Mapped[str] = mapped_column(String(20))
    proposed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    governance_proposal_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    new_abi: Mapped[dict] = mapped_column(JSON, default=dict)
    new_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    migration_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved: Mapped[bool] = mapped_column(default=False)
    executed: Mapped[bool] = mapped_column(default=False)
    proposed_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    executed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


def _utcnow():
    return datetime.now(timezone.utc)
