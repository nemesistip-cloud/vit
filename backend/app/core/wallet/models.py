import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, JSON, ForeignKey, Boolean, Enum, Text, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.database import Base
import uuid

def _new_uuid():
    return str(uuid.uuid4())

class AccountType(str, enum.Enum):
    INDIVIDUAL = "individual"
    INSTITUTIONAL = "institutional"
    SERVICE = "service"

class WalletStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"
    ARCHIVED = "archived"

class CoreAccount(Base):
    __tablename__ = "core_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    owner_id: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), default=AccountType.INDIVIDUAL)

    name: Mapped[str] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    wallets = relationship("CoreWallet", back_populates="account", cascade="all, delete-orphan")

class CoreWallet(Base):
    __tablename__ = "core_wallets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("core_accounts.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[str] = mapped_column(String(100), default="Primary Wallet")
    status: Mapped[WalletStatus] = mapped_column(Enum(WalletStatus), default=WalletStatus.ACTIVE)

    can_deposit: Mapped[bool] = mapped_column(Boolean, default=True)
    can_withdraw: Mapped[bool] = mapped_column(Boolean, default=True)
    can_transfer: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    account = relationship("CoreAccount", back_populates="wallets")
    balances = relationship("CoreBalance", back_populates="wallet", cascade="all, delete-orphan")
    addresses = relationship("CoreAddress", back_populates="wallet", cascade="all, delete-orphan")

class CoreAsset(Base):
    __tablename__ = "core_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    precision: Mapped[int] = mapped_column(Integer, default=18)
    asset_type: Mapped[str] = mapped_column(String(20), default="native")

    primary_network: Mapped[str] = mapped_column(String(50), default="vit")
    contract_address: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class CoreBalance(Base):
    __tablename__ = "core_balances"
    __table_args__ = (
        UniqueConstraint("wallet_id", "asset_symbol", name="uq_wallet_asset_balance"),
        Index("idx_balance_lookup", "wallet_id", "asset_symbol"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    wallet_id: Mapped[str] = mapped_column(String(36), ForeignKey("core_wallets.id", ondelete="CASCADE"), nullable=False)
    asset_symbol: Mapped[str] = mapped_column(String(20), ForeignKey("core_assets.symbol"), nullable=False)

    confirmed_balance: Mapped[Decimal] = mapped_column(Numeric(36, 18), default=Decimal("0"))
    pending_balance: Mapped[Decimal] = mapped_column(Numeric(36, 18), default=Decimal("0"))
    reserved_balance: Mapped[Decimal] = mapped_column(Numeric(36, 18), default=Decimal("0"))

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    wallet = relationship("CoreWallet", back_populates="balances")

class CoreAddress(Base):
    __tablename__ = "core_addresses"
    __table_args__ = (
        UniqueConstraint("network", "address", name="uq_network_address"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    wallet_id: Mapped[str] = mapped_column(String(36), ForeignKey("core_wallets.id", ondelete="CASCADE"), nullable=False)

    network: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    derivation_path: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    wallet = relationship("CoreWallet", back_populates="addresses")

class CoreWalletAudit(Base):
    __tablename__ = "core_wallet_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    wallet_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    action: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    prev_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
