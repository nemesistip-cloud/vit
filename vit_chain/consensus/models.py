"""Consensus Layer Models — Proof of Storage state tracking."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.database import Base

def _uuid() -> str:
    return str(uuid.uuid4())

class ConsensusChallenge(Base):
    __tablename__ = "consensus_challenges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    epoch: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    manifest_id: Mapped[str] = mapped_column(String(36), nullable=False)
    shard_index: Mapped[int] = mapped_column(Integer, nullable=False)
    challenge_nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    response = relationship("ChallengeResponse", back_populates="challenge", uselist=False)

class ChallengeResponse(Base):
    __tablename__ = "consensus_responses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    challenge_id: Mapped[str] = mapped_column(String(36), ForeignKey("consensus_challenges.id", ondelete="CASCADE"), unique=True, nullable=False)
    node_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    response_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    response_signature: Mapped[str] = mapped_column(Text, nullable=False)
    responded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    challenge = relationship("ConsensusChallenge", back_populates="response")
