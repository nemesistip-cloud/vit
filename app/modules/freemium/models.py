"""Freemium module database models."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.database import Base

class IQTestQuestion(Base):
    """Questions for the VIT Intelligence Assessment (IQ Test)."""
    __tablename__ = "iq_test_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    q: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list] = mapped_column(JSON, nullable=False)  # List of strings
    correct: Mapped[int] = mapped_column(Integer, nullable=False) # Index of correct option
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UserIQTestResult(Base):
    """Results of users taking the IQ Test."""
    __tablename__ = "user_iq_test_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    iq_score: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    answers: Mapped[dict] = mapped_column(JSON, nullable=False) # Map of question_id -> selected_index
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")

class OracleMicEpisode(Base):
    """AI-generated podcast episodes for the Oracle Mic section."""
    __tablename__ = "oracle_mic_episodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True) # UUID or slug
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    host: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[str] = mapped_column(String(50), nullable=False) # Display date string
    length: Mapped[str] = mapped_column(String(20), nullable=False) # Duration string like "05:42"
    premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
