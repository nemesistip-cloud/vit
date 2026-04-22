# app/modules/marketplace/models.py
"""AI Marketplace database models — Module G."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class AIModelListing(Base):
    """G1 — One listing per model offered on the marketplace."""
    __tablename__ = "marketplace_listings"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    creator_id      : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Identity
    name            : Mapped[str]      = mapped_column(String(128), nullable=False)
    slug            : Mapped[str]      = mapped_column(String(128), unique=True, nullable=False, index=True)
    description     : Mapped[str]      = mapped_column(Text, nullable=True)
    category        : Mapped[str]      = mapped_column(String(64), default="prediction", nullable=False)
    tags            : Mapped[str]      = mapped_column(String(255), nullable=True)   # comma-separated

    # Pricing (VITCoin per call)
    price_per_call  : Mapped[Decimal]  = mapped_column(Numeric(20, 8), default=Decimal("1.00000000"), nullable=False)

    # Listing upload fee (paid in VITCoin at listing time)
    listing_fee_paid: Mapped[Decimal]  = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"), nullable=False)

    # Link to internal model registry (optional — third-party models may not have one)
    model_key       : Mapped[str]      = mapped_column(String(64), nullable=True)    # ModelMetadata.key

    # Uploaded .pkl file path (relative to models/ directory)
    pkl_path        : Mapped[str]      = mapped_column(String(512), nullable=True)
    file_size_bytes : Mapped[int]      = mapped_column(Integer, nullable=True)
    pkl_sha256      : Mapped[str]      = mapped_column(String(64), nullable=True)    # file integrity hash

    # External webhook (for third-party hosted models)
    webhook_url     : Mapped[str]      = mapped_column(String(512), nullable=True)
    webhook_secret  : Mapped[str]      = mapped_column(String(256), nullable=True)

    # Admin approval workflow
    # approval_status: pending | approved | rejected | suspended
    approval_status : Mapped[str]      = mapped_column(String(20), default="pending", nullable=False, index=True)
    approval_note   : Mapped[str]      = mapped_column(Text, nullable=True)
    approved_by     : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at     : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Revenue
    total_revenue   : Mapped[Decimal]  = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))
    creator_revenue : Mapped[Decimal]  = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))
    protocol_revenue: Mapped[Decimal]  = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))
    PROTOCOL_FEE    = Decimal("0.15")  # 15 % to protocol

    # Reputation
    usage_count     : Mapped[int]      = mapped_column(Integer, default=0)
    rating_sum      : Mapped[float]    = mapped_column(Float, default=0.0)
    rating_count    : Mapped[int]      = mapped_column(Integer, default=0)

    # State
    is_active       : Mapped[bool]     = mapped_column(Boolean, default=False)  # False until admin-approved
    is_verified     : Mapped[bool]     = mapped_column(Boolean, default=False)  # admin-verified quality badge

    created_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    creator  = relationship("User", foreign_keys=[creator_id], backref="marketplace_listings")
    approver = relationship("User", foreign_keys=[approved_by])
    usages   = relationship("ModelUsageLog", back_populates="listing", cascade="all, delete-orphan")
    ratings  = relationship("ModelRating",   back_populates="listing", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_listing_creator_id",       "creator_id"),
        Index("idx_listing_category",         "category"),
        Index("idx_listing_is_active",        "is_active"),
        Index("idx_listing_approval_status",  "approval_status"),
    )

    @property
    def avg_rating(self) -> float:
        return round(self.rating_sum / self.rating_count, 2) if self.rating_count else 0.0


class ModelUsageLog(Base):
    """G2 — One row per paid model call."""
    __tablename__ = "marketplace_usage_logs"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    listing_id      : Mapped[int]      = mapped_column(Integer, ForeignKey("marketplace_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    caller_id       : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    vitcoin_charged : Mapped[Decimal]  = mapped_column(Numeric(20, 8), nullable=False)
    creator_share   : Mapped[Decimal]  = mapped_column(Numeric(20, 8), nullable=False)
    protocol_share  : Mapped[Decimal]  = mapped_column(Numeric(20, 8), nullable=False)

    # Request / response payload (summary only — keep it lean)
    input_summary   : Mapped[str]      = mapped_column(Text, nullable=True)
    output_summary  : Mapped[str]      = mapped_column(Text, nullable=True)
    status          : Mapped[str]      = mapped_column(String(20), default="success")   # success / failed
    error_message   : Mapped[str]      = mapped_column(Text, nullable=True)

    called_at       : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listing = relationship("AIModelListing", back_populates="usages")
    caller  = relationship("User", foreign_keys=[caller_id])

    __table_args__ = (
        Index("idx_usage_listing_id", "listing_id"),
        Index("idx_usage_caller_id",  "caller_id"),
        Index("idx_usage_called_at",  "called_at"),
    )


class ModelRating(Base):
    """G3 — One rating per user per listing."""
    __tablename__ = "marketplace_ratings"

    id          : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    listing_id  : Mapped[int]      = mapped_column(Integer, ForeignKey("marketplace_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id     : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    stars       : Mapped[int]      = mapped_column(Integer, nullable=False)   # 1-5
    review      : Mapped[str]      = mapped_column(Text, nullable=True)
    created_at  : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listing = relationship("AIModelListing", back_populates="ratings")
    user    = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("listing_id", "user_id", name="uq_rating_listing_user"),
        Index("idx_rating_listing_id", "listing_id"),
    )
