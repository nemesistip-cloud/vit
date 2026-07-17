"""Training module database models — Module D1.

Uses UUIDs throughout for Phase 2 migration compatibility.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index,
    Integer, JSON, Numeric, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class TrainingJobStatus(PyEnum):
    UPLOADING = "uploading"
    VALIDATING = "validating"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ModuleTrainingJob(Base):
    """A data upload + quality-score + prompt-generation job (Module D)."""
    __tablename__ = "module_training_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    status: Mapped[str] = mapped_column(String(20), default=TrainingJobStatus.UPLOADING.value)
    league: Mapped[str] = mapped_column(String(100), nullable=False)
    team_filter: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    date_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    column_profile: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    quality_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    quality_breakdown: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    generated_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    vitcoin_reward: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    vitcoin_earned: Mapped[bool] = mapped_column(Boolean, default=False)

    model_accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    improvement_suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    guide_steps = relationship(
        "ModuleTrainingGuideStep", back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_module_tj_user_id", "user_id"),
        Index("idx_module_tj_status", "status"),
        Index("idx_module_tj_submitted_at", "submitted_at"),
    )


class ModuleTrainingGuideStep(Base):
    """Step-by-step guide generated for a training job."""
    __tablename__ = "module_training_guide_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("module_training_jobs.id", ondelete="CASCADE"), nullable=False
    )

    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_columns: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    example_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tips: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    job = relationship("ModuleTrainingJob", back_populates="guide_steps")

    __table_args__ = (Index("idx_module_tgs_job_id", "job_id"),)
