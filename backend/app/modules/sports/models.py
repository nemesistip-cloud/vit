from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class MarketMapping(Base):
    __tablename__ = "market_mappings"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), index=True)
    internal_market_id = Column(String(36), ForeignKey("markets.id"), nullable=True, index=True)
    provider_name = Column(String(50), nullable=False)
    external_match_id = Column(String(100), nullable=True, index=True)
    external_selection_id = Column(String(100), nullable=True)
    market_type = Column(String(50), nullable=True)
    selection_name = Column(String(50), nullable=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    match = relationship("Match", foreign_keys=[match_id], overlaps="match_mapping_match")

class AffiliateClick(Base):
    __tablename__ = "affiliate_clicks"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    provider_name = Column(String(50))
    market_type = Column(String(50))
    selection_name = Column(String(50))

    utm_source = Column(String(100))
    utm_medium = Column(String(100))
    utm_campaign = Column(String(100))
    utm_content = Column(String(100))

    ip_address = Column(String(45))
    user_agent = Column(String(255))

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ResultObservation(Base):
    """Auditable history of raw result observations from external providers."""
    __tablename__ = "result_observations"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    provider_name = Column(String(50), nullable=False, index=True)
    provider_event_id = Column(String(100), nullable=True, index=True)

    competition_name = Column(String(100), nullable=True)
    home_team = Column(String(100), nullable=True)
    away_team = Column(String(100), nullable=True)

    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)
    reported_outcome = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="scheduled", index=True)  # full_time, extra_time, penalty, scheduled, in_progress, postponed, abandoned, cancelled, unknown

    provider_timestamp = Column(DateTime(timezone=True), nullable=True)
    local_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    validation_outcome = Column(String(100), nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    raw_payload = Column(JSON, nullable=True)

    match = relationship("Match", foreign_keys=[match_id])


class ResultVerification(Base):
    """Consolidated verification state for canonical match results."""
    __tablename__ = "result_verifications"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, unique=True, index=True)

    # Verification status: PENDING_RESULT, PENDING_VERIFICATION, VERIFIED, NEEDS_REVIEW, CORRECTION_DETECTED, UNAVAILABLE
    verification_status = Column(String(50), nullable=False, default="PENDING_RESULT", index=True)

    primary_provider = Column(String(50), nullable=True)
    secondary_provider = Column(String(50), nullable=True)

    verified_home_goals = Column(Integer, nullable=True)
    verified_away_goals = Column(Integer, nullable=True)
    verified_outcome = Column(String(50), nullable=True)

    source_count = Column(Integer, nullable=False, default=0)
    agreement_ratio = Column(Float, nullable=False, default=1.0)
    verification_reason = Column(Text, nullable=True)

    is_correction = Column(Boolean, nullable=False, default=False)
    correction_history = Column(JSON, nullable=True, default=list)

    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    match = relationship("Match", foreign_keys=[match_id])
