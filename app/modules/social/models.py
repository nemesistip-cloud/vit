import uuid
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, UniqueConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class CandidateState(str, Enum):
    NEW = "NEW"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    READY_FOR_DISTRIBUTION = "READY_FOR_DISTRIBUTION"
    PUBLISHED = "PUBLISHED"


class PublicationStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class SocialSignal(Base):
    __tablename__ = "social_signals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    source = Column(String(100), nullable=False, index=True)
    url = Column(String(500), nullable=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    topic = Column(String(100), nullable=True, index=True)
    entities = Column(JSON, default=list)
    evidence = Column(JSON, default=dict)
    freshness_seconds = Column(Integer, default=0)
    confidence = Column(Float, default=1.0)
    verification_status = Column(String(50), default="VERIFIED")
    deduplication_key = Column(String(255), unique=True, index=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    opportunities = relationship("SocialOpportunity", back_populates="signal", cascade="all, delete-orphan")


class SocialOpportunity(Base):
    __tablename__ = "social_opportunities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    signal_id = Column(String(36), ForeignKey("social_signals.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False, default=0.0)
    score_breakdown = Column(JSON, default=dict)
    reasoning = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)
    priority = Column(String(20), default="MEDIUM")
    risk_flags = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    signal = relationship("SocialSignal", back_populates="opportunities")
    candidates = relationship("SocialCandidate", back_populates="opportunity", cascade="all, delete-orphan")


class SocialCandidate(Base):
    __tablename__ = "social_candidates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    opportunity_id = Column(String(36), ForeignKey("social_opportunities.id", ondelete="CASCADE"), nullable=False, index=True)
    generated_content = Column(Text, nullable=False)
    content_format = Column(String(50), default="TEXT")
    provenance = Column(JSON, default=dict)
    risk_flags = Column(JSON, default=list)
    state = Column(String(50), nullable=False, default=CandidateState.NEW.value, index=True)
    review_history = Column(JSON, default=list)

    created_by = Column(String(100), nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    opportunity = relationship("SocialOpportunity", back_populates="candidates")
    publication_records = relationship("SocialPublicationRecord", back_populates="candidate", cascade="all, delete-orphan")


class SocialPublicationRecord(Base):
    __tablename__ = "social_publication_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    candidate_id = Column(String(36), ForeignKey("social_candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, default=PublicationStatus.PENDING.value, index=True)
    external_ref = Column(String(255), nullable=True)
    url = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("candidate_id", "platform", name="uq_candidate_platform_publication"),
    )

    candidate = relationship("SocialCandidate", back_populates="publication_records")
