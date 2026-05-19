"""Module F — MatchFeatureStore: persistent computed features for every upcoming match."""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, JSON, Index
)
from sqlalchemy.sql import func

from app.db.database import Base


class MatchFeatureStore(Base):
    """
    Stores the fully-engineered feature vector for each upcoming match.

    Populated by the ETL pipeline every 6 hours and updated in real-time
    when fresh odds arrive via the WebSocket odds refresher.
    """
    __tablename__ = "match_feature_store"

    id = Column(Integer, primary_key=True, index=True)

    # --- Identity ---
    match_id = Column(String, unique=True, index=True, nullable=False)   # external API id
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    league = Column(String, nullable=False, index=True)
    kickoff_time = Column(DateTime, nullable=True)

    # --- Feature payload ---
    features = Column(JSON, nullable=False, default=dict)       # engineered features
    odds_snapshot = Column(JSON, nullable=True)                  # latest raw odds
    injury_snapshot = Column(JSON, nullable=True)                # injury data at ingestion time

    # --- Data quality ---
    source_quality = Column(Float, default=0.0)   # 0-1: completeness of input data
    pipeline_version = Column(String, default="1.0")
    is_stale = Column(Boolean, default=False)      # True when past kickoff with no update

    # --- Timestamps ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_feature_store_league_kickoff", "league", "kickoff_time"),
    )


class PipelineRun(Base):
    """Audit log for each ETL pipeline execution."""
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)

    run_type = Column(String, nullable=False)         # "scheduled" | "manual" | "odds_refresh"
    status = Column(String, nullable=False)           # "running" | "success" | "failed"
    leagues_processed = Column(JSON, default=list)
    matches_upserted = Column(Integer, default=0)
    matches_skipped = Column(Integer, default=0)
    errors = Column(JSON, default=list)

    duration_seconds = Column(Float, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
