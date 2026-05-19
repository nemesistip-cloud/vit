"""app/modules/prophecy_chain/models.py — models for the Prophecy Chain progression system."""

from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class ProphecyChapter(Base):
    __tablename__ = "prophecy_chapters"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    sequence_order = Column(Integer, default=0)

    # Requirements to unlock
    required_predictions = Column(Integer, default=0)
    required_accuracy = Column(Float, default=0.0)
    required_streak = Column(Integer, default=0)

    # Rewards
    reward_vit = Column(Integer, default=0)
    reward_xp = Column(Integer, default=0)
    reward_badge = Column(String(100), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserProphecyProgress(Base):
    __tablename__ = "user_prophecy_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    current_chapter_id = Column(Integer, ForeignKey("prophecy_chapters.id"))

    chapters_completed = Column(JSON, default=list)  # List of chapter IDs

    total_qualified_predictions = Column(Integer, default=0)
    total_qualified_wins = Column(Integer, default=0)
    current_accuracy = Column(Float, default=0.0)

    last_evaluated_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="prophecy_progress")
    current_chapter = relationship("ProphecyChapter")
