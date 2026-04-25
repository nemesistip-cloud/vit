"""Task system database models — Module T."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import DECIMAL

from app.db.database import Base


class TaskType(PyEnum):
    ONE_TIME = "one_time"      # Complete once, earn reward
    DAILY = "daily"           # Reset daily
    WEEKLY = "weekly"         # Reset weekly
    MONTHLY = "monthly"       # Reset monthly
    PROGRESS = "progress"     # Accumulate progress over time


class TaskStatus(PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"


class TaskCategory(Base):
    """Task categories for organization."""
    __tablename__ = "task_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(50), nullable=True)  # Icon name
    color: Mapped[str] = mapped_column(String(20), nullable=True)  # Color class
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tasks = relationship("Task", back_populates="category", cascade="all, delete-orphan")


class Task(Base):
    """Admin-created tasks that users can complete for VIT rewards."""
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("task_categories.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[str] = mapped_column(String(100), nullable=True)
    task_type: Mapped[str] = mapped_column(Enum(TaskType), nullable=False)
    status: Mapped[str] = mapped_column(Enum(TaskStatus), default=TaskStatus.ACTIVE, nullable=False)

    # Requirements
    required_count: Mapped[int] = mapped_column(Integer, default=1)  # For progress tasks
    max_completions: Mapped[int] = mapped_column(Integer, default=1)  # How many times can be completed

    # Rewards
    vit_reward: Mapped[DECIMAL] = mapped_column(Numeric(20, 8), default=0)
    xp_reward: Mapped[int] = mapped_column(Integer, default=0)

    # Timing
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    reset_period_days: Mapped[int] = mapped_column(Integer, nullable=True)  # For recurring tasks

    # Metadata
    icon: Mapped[str] = mapped_column(String(50), nullable=True)
    color: Mapped[str] = mapped_column(String(20), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)  # Additional requirements

    # Audit
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    category = relationship("TaskCategory", back_populates="tasks")
    completions = relationship("UserTaskCompletion", back_populates="task", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])


class UserTaskCompletion(Base):
    """Tracks user progress and completions of tasks."""
    __tablename__ = "user_task_completions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id"), nullable=False)

    # Progress tracking
    current_progress: Mapped[int] = mapped_column(Integer, default=0)
    required_progress: Mapped[int] = mapped_column(Integer, default=1)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Completion tracking
    completed_count: Mapped[int] = mapped_column(Integer, default=0)  # How many times completed
    last_completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    next_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Rewards earned
    total_vit_earned: Mapped[DECIMAL] = mapped_column(Numeric(20, 8), default=0)
    total_xp_earned: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="task_completions")
    task = relationship("Task", back_populates="completions")

    __table_args__ = (
        {'sqlite_autoincrement': True},  # For SQLite
    )