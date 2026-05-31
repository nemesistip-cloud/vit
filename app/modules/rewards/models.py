from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class OfferCompletion(Base):
    __tablename__ = "offer_completions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    reward_type: Mapped[str] = mapped_column(String(30), default="offer", nullable=False)
    provider_offer_id: Mapped[str] = mapped_column(String(128), nullable=True)
    provider_event_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="VITCoin", nullable=False)
    reward_margin: Mapped[float] = mapped_column(Float, default=0.30)
    wallet_tx_id: Mapped[str] = mapped_column(String(36), nullable=True)
    provider_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    provider_payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_signature: Mapped[str] = mapped_column(String(255), nullable=True)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    audit_logs = relationship("PostbackAuditLog", back_populates="offer_completion", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("provider", "provider_payload_hash", name="uq_offer_completions_provider_payload"),
        Index("idx_offer_completions_status", "status"),
    )


class PostbackAuditLog(Base):
    __tablename__ = "postback_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    offer_completion_id: Mapped[int] = mapped_column(Integer, ForeignKey("offer_completions.id", ondelete="CASCADE"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    headers: Mapped[dict] = mapped_column(JSON, default=dict)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    signature: Mapped[str] = mapped_column(String(255), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="unknown", nullable=False)
    validation_details: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str] = mapped_column(String(500), nullable=True)

    offer_completion = relationship("OfferCompletion", back_populates="audit_logs")
