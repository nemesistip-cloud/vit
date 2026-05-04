"""System Identity models — VIT Platform v4.

Each user is issued a unique, human-readable System ID upon first request.
The ID is cryptographically derived and cannot be changed. It serves as the
user's canonical on-platform identity, separate from their username/email.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer,
    JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class IDTier(str, enum.Enum):
    BASIC   = "basic"    # email verified only
    STANDARD= "standard" # KYC submitted
    VERIFIED= "verified" # KYC approved
    ELITE   = "elite"    # verified + validator / subscriber


class SystemID(Base):
    """A unique, persistent system identity issued to every platform user."""
    __tablename__ = "system_ids"
    __table_args__ = (
        UniqueConstraint("user_id"),
        UniqueConstraint("sid"),
        Index("idx_system_ids_user", "user_id"),
        Index("idx_system_ids_sid", "sid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # The canonical system identifier  e.g.  VIT-2024-A3F9K1
    sid: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Display / card metadata
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    tier: Mapped[IDTier] = mapped_column(default=IDTier.BASIC)
    avatar_initials: Mapped[str] = mapped_column(String(4), nullable=False, default="VIT")

    # Linked DID (optional — set when user registers a DID)
    did: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Card metadata — serialized badge/claims
    badges: Mapped[dict] = mapped_column(JSON, default=dict)

    # Lifecycle
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
