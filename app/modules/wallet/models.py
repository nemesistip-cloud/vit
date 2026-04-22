# app/modules/wallet/models.py
"""Wallet and payment database models — SQLite + PostgreSQL compatible."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey, Integer,
    JSON, Numeric, String, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ── Enums ─────────────────────────────────────────────────────────────

class Currency(PyEnum):
    NGN = "NGN"
    USD = "USD"
    USDT = "USDT"
    PI = "PI"
    VITCOIN = "VITCoin"


class TransactionType(PyEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    SUBSCRIPTION = "subscription"
    CONVERSION = "conversion"
    EARN = "earn"
    SPEND = "spend"
    FEE = "fee"
    STAKE = "stake"
    REWARD = "reward"
    SLASH = "slash"


class TransactionDirection(PyEnum):
    CREDIT = "credit"
    DEBIT = "debit"


class TransactionStatus(PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REVERSED = "reversed"


class WithdrawalStatus(PyEnum):
    PENDING = "pending"
    AUTO_APPROVED = "auto_approved"
    MANUAL_REVIEW = "manual_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"
    FAILED = "failed"


class SubscriptionStatus(PyEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class DestinationType(PyEnum):
    BANK_ACCOUNT = "bank_account"
    USDT_ADDRESS = "usdt_address"
    PI_WALLET = "pi_wallet"
    PAYPAL = "paypal"
    OTHER = "other"


# ── Models ─────────────────────────────────────────────────────────────

class Wallet(Base):
    """User wallet — one per user, holds multi-currency balances."""
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    ngn_balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))
    usd_balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))
    usdt_balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))
    pi_balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))
    vitcoin_balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))

    is_frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    kyc_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")
    withdrawal_requests = relationship("WithdrawalRequest", back_populates="wallet")

    __table_args__ = (
        Index("idx_wallets_user_id", "user_id"),
        Index("idx_wallets_is_frozen", "is_frozen"),
    )


class WalletTransaction(Base):
    """Individual wallet transaction record."""
    __tablename__ = "wallet_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wallet_id: Mapped[str] = mapped_column(String(36), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)

    type: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rate_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    fee_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))
    fee_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    tx_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    wallet = relationship("Wallet", back_populates="transactions")

    __table_args__ = (
        Index("idx_wallet_tx_user_id", "user_id"),
        Index("idx_wallet_tx_wallet_id", "wallet_id"),
        Index("idx_wallet_tx_type", "type"),
        Index("idx_wallet_tx_currency", "currency"),
        Index("idx_wallet_tx_status", "status"),
        Index("idx_wallet_tx_created_at", "created_at"),
        UniqueConstraint("reference", name="uq_wallet_transactions_reference"),
    )


class WalletSubscriptionPlan(Base):
    """Multi-currency subscription plans (wallet-owned)."""
    __tablename__ = "wallet_subscription_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    features: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    price_ngn: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    price_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    price_usdt: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    price_pi: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    price_vitcoin: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    wallet_user_subscriptions = relationship("WalletUserSubscription", back_populates="plan")


class WalletUserSubscription(Base):
    """User's active wallet subscription."""
    __tablename__ = "wallet_user_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("wallet_subscription_plans.id"), nullable=False)

    currency_paid: Mapped[str] = mapped_column(String(10), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="active")

    renewal_tx_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("wallet_transactions.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    plan = relationship("WalletSubscriptionPlan", back_populates="wallet_user_subscriptions")

    __table_args__ = (
        Index("idx_wallet_subs_user_id", "user_id"),
        Index("idx_wallet_subs_status", "status"),
        Index("idx_wallet_subs_expires_at", "expires_at"),
    )


class WithdrawalRequest(Base):
    """User withdrawal request."""
    __tablename__ = "withdrawal_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wallet_id: Mapped[str] = mapped_column(String(36), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)

    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_type: Mapped[str] = mapped_column(String(30), nullable=False)

    status: Mapped[str] = mapped_column(String(30), default="pending")
    auto_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    wallet = relationship("Wallet", back_populates="withdrawal_requests")

    __table_args__ = (
        Index("idx_withdrawal_user_id", "user_id"),
        Index("idx_withdrawal_status", "status"),
        Index("idx_withdrawal_requested_at", "requested_at"),
    )


class PlatformConfig(Base):
    """Platform configuration key-value store."""
    __tablename__ = "platform_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VITCoinPriceHistory(Base):
    """Historical VITCoin prices."""
    __tablename__ = "vitcoin_price_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    price_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    circulating_supply: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    rolling_revenue_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_vitcoin_price_calculated_at", "calculated_at"),
    )
