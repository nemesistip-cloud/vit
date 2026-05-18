"""Prophecy Chain — Narrative + Merit Progression Engine models."""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy import ForeignKey, Numeric, String, Text, JSON, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base

class ChapterTier(str, enum.Enum):
    INITIATE = "initiate"
    PATTERN_RECOGNITION = "pattern_recognition"
    SIGNAL_HUNTER = "signal_hunter"
    CONSENSUS_BREAKER = "consensus_breaker"
    RISK_MASTERY = "risk_mastery"
    RISK_ARCHITECT = "risk_architect"
    ORACLE = "oracle"
    ARCHITECT = "architect"
    VALIDATOR = "validator"

class ProphecyChapter(Base):
    """Canonical progression chapters seeded via migration."""
    __tablename__ = "prophecy_chapters"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    lore: Mapped[str] = mapped_column(Text, nullable=True)
    tier: Mapped[ChapterTier] = mapped_column(nullable=False)

    # Requirements configuration (JSON)
    # { "min_predictions": 5, "min_odds": 1.35, "min_accuracy": 0.4, "min_unique_leagues": 2 }
    requirements: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Reward configuration (JSON)
    # { "vit": 10, "xp": 50, "badge": "Genesis Badge", "title": "Initiate" }
    reward_config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    unlock_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user_progress: Mapped[list["UserProphecyProgress"]] = relationship(back_populates="chapter")

class UserProphecyProgress(Base):
    """Tracks individual user progress through prophecy chapters."""
    __tablename__ = "user_prophecy_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("prophecy_chapters.id", ondelete="CASCADE"))

    # Current progress state (JSON)
    # { "predictions_count": 3, "current_accuracy": 0.66, "leagues": ["PL", "SA"] }
    progress_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    chapter: Mapped["ProphecyChapter"] = relationship(back_populates="user_progress")

class ProphecyEvent(Base):
    """Append-only event log for auditing and progression triggers."""
    __tablename__ = "prophecy_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True) # e.g., "prediction_submitted", "chapter_unlocked"

    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Cryptographic proof or signature (Phase 4 placeholder)
    signature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UserMeritSnapshot(Base):
    """Immutable snapshots of user merit for audit and progression history."""
    __tablename__ = "user_merit_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    accuracy: Mapped[float] = mapped_column(Numeric(5, 4))
    qualified_predictions: Mapped[int] = mapped_column(Integer)
    avg_odds: Mapped[float] = mapped_column(Numeric(6, 3))
    merit_score: Mapped[float] = mapped_column(Numeric(16, 4))
    trust_score: Mapped[float] = mapped_column(Numeric(5, 4))
    unique_leagues: Mapped[int] = mapped_column(Integer)

    # Context (e.g., "chapter_completed: Initiation")
    snapshot_trigger: Mapped[str] = mapped_column(String(100))

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
