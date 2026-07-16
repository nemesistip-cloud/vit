"""Consensus Layer Models — Proof of Storage and Validator state tracking."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Boolean, Text, Float, JSON
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

class Validator(Base):
    __tablename__ = "validators"
    node_id: Mapped[str] = mapped_column(String(255), primary_key=True) # did:vit:agent:...
    public_key: Mapped[str] = mapped_column(String(130), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active") # active, jailed, inactive
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    reputation = relationship("ValidatorReputation", back_populates="validator", uselist=False)

class ValidatorReputation(Base):
    __tablename__ = "validator_reputation"
    node_id: Mapped[str] = mapped_column(String(255), ForeignKey("validators.node_id", ondelete="CASCADE"), primary_key=True)
    score: Mapped[float] = mapped_column(Float, default=1.0)
    blocks_produced: Mapped[int] = mapped_column(Integer, default=0)
    blocks_missed: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_misses: Mapped[int] = mapped_column(Integer, default=0)
    uptime_pct: Mapped[float] = mapped_column(Float, default=100.0)

    validator = relationship("Validator", back_populates="reputation")

class ConsensusCheckpoint(Base):
    __tablename__ = "consensus_checkpoints"
    height: Mapped[int] = mapped_column(Integer, primary_key=True)
    block_hash: Mapped[str] = mapped_column(String(66), nullable=False, unique=True)
    state_root: Mapped[str] = mapped_column(String(66), nullable=False)
    validator_set_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
