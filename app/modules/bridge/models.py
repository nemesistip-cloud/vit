# app/modules/bridge/models.py
"""Cross-Chain & Bridge Layer database models — Module J."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, Integer,
    Numeric, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class BridgePool(Base):
    """J1 — Liquidity pool for each supported chain/asset pair."""
    __tablename__ = "bridge_pools"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    asset_from      : Mapped[str]      = mapped_column(String(16), nullable=False)   # e.g. VIT
    asset_to        : Mapped[str]      = mapped_column(String(16), nullable=False)   # e.g. USDT
    chain_from      : Mapped[str]      = mapped_column(String(32), nullable=False)   # e.g. VIT_NETWORK
    chain_to        : Mapped[str]      = mapped_column(String(32), nullable=False)   # e.g. ETHEREUM
    exchange_rate   : Mapped[Decimal]  = mapped_column(Numeric(20, 8), nullable=False)
    fee_pct         : Mapped[Decimal]  = mapped_column(Numeric(10, 4), default=Decimal("0.0100"))  # 1 %
    min_amount      : Mapped[Decimal]  = mapped_column(Numeric(20, 8), default=Decimal("10.00000000"))
    max_amount      : Mapped[Decimal]  = mapped_column(Numeric(20, 8), default=Decimal("10000.00000000"))
    pool_liquidity  : Mapped[Decimal]  = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))
    is_active       : Mapped[bool]     = mapped_column(Boolean, default=True)

    created_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    transactions = relationship("BridgeTransaction", back_populates="pool", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_bridge_pool_assets", "asset_from", "asset_to"),
    )


class BridgeTransaction(Base):
    """J2 — One row per bridge transfer (lock/mint or burn/release)."""
    __tablename__ = "bridge_transactions"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    pool_id         : Mapped[int]      = mapped_column(Integer, ForeignKey("bridge_pools.id"), nullable=False, index=True)
    user_id         : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    tx_hash         : Mapped[str]      = mapped_column(String(128), unique=True, nullable=False, index=True)
    direction       : Mapped[str]      = mapped_column(String(16), nullable=False)   # outbound | inbound
    # direction outbound = user sends VIT → receives USDT/ETH on target chain
    # direction inbound  = user sends USDT/ETH → receives VIT

    amount_in       : Mapped[Decimal]  = mapped_column(Numeric(20, 8), nullable=False)
    amount_out      : Mapped[Decimal]  = mapped_column(Numeric(20, 8), nullable=False)
    fee             : Mapped[Decimal]  = mapped_column(Numeric(20, 8), nullable=False)
    exchange_rate   : Mapped[Decimal]  = mapped_column(Numeric(20, 8), nullable=False)

    destination_address : Mapped[str] = mapped_column(String(255), nullable=False)
    source_address      : Mapped[str] = mapped_column(String(255), nullable=True)

    # State machine: pending → locked → confirmed → completed | failed | disputed
    status          : Mapped[str]      = mapped_column(String(20), default="pending")
    status_message  : Mapped[str]      = mapped_column(Text, nullable=True)

    # Relayer proof fields
    relayer_tx_hash : Mapped[str]      = mapped_column(String(128), nullable=True)
    confirmed_at    : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at    : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pool = relationship("BridgePool", back_populates="transactions")
    user = relationship("User", foreign_keys=[user_id])
    audit_logs = relationship("BridgeAuditLog", back_populates="transaction", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_bridge_tx_user_id",    "user_id"),
        Index("idx_bridge_tx_status",     "status"),
        Index("idx_bridge_tx_created_at", "created_at"),
    )


class BridgeAuditLog(Base):
    """J2 — Immutable event log for each status change on a bridge tx."""
    __tablename__ = "bridge_audit_logs"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    transaction_id  : Mapped[int]      = mapped_column(Integer, ForeignKey("bridge_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    event           : Mapped[str]      = mapped_column(String(64), nullable=False)    # initiated | locked | relayer_confirmed | completed | failed
    actor           : Mapped[str]      = mapped_column(String(32), default="system")  # system | relayer | admin | user
    detail          : Mapped[str]      = mapped_column(Text, nullable=True)
    created_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transaction = relationship("BridgeTransaction", back_populates="audit_logs")
