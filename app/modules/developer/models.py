# app/modules/developer/models.py
"""Developer Platform & SDK database models — Module L."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class APIKey(Base):
    """L1 — Developer API key."""
    __tablename__ = "dev_api_keys"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    user_id         : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name            : Mapped[str]      = mapped_column(String(128), nullable=False)
    key_prefix      : Mapped[str]      = mapped_column(String(12), nullable=False)        # first 12 chars — shown to user
    key_hash        : Mapped[str]      = mapped_column(String(128), unique=True, nullable=False)  # bcrypt hash
    key_plain       : Mapped[str]      = mapped_column(String(64), nullable=True)         # shown once on creation, then nulled

    plan            : Mapped[str]      = mapped_column(String(32), default="free")        # free | starter | pro | enterprise
    rate_limit_rpm  : Mapped[int]      = mapped_column(Integer, default=60)               # requests per minute
    rate_limit_rpd  : Mapped[int]      = mapped_column(Integer, default=1000)             # requests per day

    is_active       : Mapped[bool]     = mapped_column(Boolean, default=True)
    last_used_at    : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    total_requests  : Mapped[int]      = mapped_column(Integer, default=0)
    total_vitcoin_billed : Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))

    created_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    user        = relationship("User", foreign_keys=[user_id])
    usage_logs  = relationship("APIUsageLog", back_populates="api_key", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_dev_key_user_id",   "user_id"),
        Index("idx_dev_key_prefix",    "key_prefix"),
        Index("idx_dev_key_is_active", "is_active"),
    )


class APIUsageLog(Base):
    """L2 — One row per authenticated API call made with a developer key."""
    __tablename__ = "dev_api_usage_logs"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    api_key_id      : Mapped[int]      = mapped_column(Integer, ForeignKey("dev_api_keys.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id         : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    endpoint        : Mapped[str]      = mapped_column(String(255), nullable=False)
    method          : Mapped[str]      = mapped_column(String(8), nullable=False)         # GET | POST | …
    status_code     : Mapped[int]      = mapped_column(Integer, nullable=False)
    latency_ms      : Mapped[int]      = mapped_column(Integer, nullable=True)

    vitcoin_billed  : Mapped[Decimal]  = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))

    ip_address      : Mapped[str]      = mapped_column(String(45), nullable=True)
    user_agent      : Mapped[str]      = mapped_column(String(255), nullable=True)

    called_at       : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    api_key = relationship("APIKey", back_populates="usage_logs")
    user    = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_dev_usage_key_id",   "api_key_id"),
        Index("idx_dev_usage_user_id",  "user_id"),
        Index("idx_dev_usage_called_at","called_at"),
    )


class APIKeyPlan(Base):
    """L3 — Plan definitions (admin-managed)."""
    __tablename__ = "dev_api_plans"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    name            : Mapped[str]      = mapped_column(String(32), unique=True, nullable=False)
    display_name    : Mapped[str]      = mapped_column(String(64), nullable=False)
    rate_limit_rpm  : Mapped[int]      = mapped_column(Integer, nullable=False)
    rate_limit_rpd  : Mapped[int]      = mapped_column(Integer, nullable=False)
    price_vitcoin_per_1k : Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))
    description     : Mapped[str]      = mapped_column(Text, nullable=True)
    is_active       : Mapped[bool]     = mapped_column(Boolean, default=True)

    created_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
