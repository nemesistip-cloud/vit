# app/modules/ai/models.py
"""
Module E — Database Models

E1. ModelMetadata   — registry row for every model in the ensemble
E4. AIPredictionAudit — full audit record for every ensemble prediction
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, JSON, String, Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.db.database import Base


class ModelMetadata(Base):
    """
    E1 — Model Registry

    One row per model key.  Weights here are the authoritative source;
    the in-memory orchestrator is synced from this table at startup and
    after every weight-adjuster run.
    """
    __tablename__ = "model_metadata"

    id          = Column(Integer, primary_key=True, index=True)
    key         = Column(String(64), unique=True, nullable=False, index=True)
    name        = Column(String(128), nullable=False)
    model_type  = Column(String(64), nullable=False)
    version     = Column(String(32), default="v3.1.0")

    # Performance tracking
    weight          = Column(Float, default=1.0)       # ensemble vote weight
    accuracy        = Column(Float, nullable=True)     # last settled accuracy (0-1)
    accuracy_1x2    = Column(Float, nullable=True)
    accuracy_ou     = Column(Float, nullable=True)     # over/under
    brier_score     = Column(Float, nullable=True)
    log_loss        = Column(Float, nullable=True)
    clv_score       = Column(Float, nullable=True)     # rolling EMA of CLV-weighted contribution; positive = beats market
    clv_samples     = Column(Integer, default=0)       # how many settled matches had a CLV signal contribute
    predictions_total = Column(Integer, default=0)
    predictions_correct = Column(Integer, default=0)

    # State
    is_active   = Column(Boolean, default=True)
    pkl_loaded  = Column(Boolean, default=False)
    pkl_path    = Column(String(512), nullable=True)
    training_samples = Column(Integer, default=0)

    # Promotion / version history
    # active_version: the version currently promoted into production
    # version_history: list of {version, pkl_path, uploaded_at, metrics, training_samples, promoted_at}
    active_version  = Column(String(32), nullable=True)
    version_history = Column(JSON, default=list)

    # Markets this model supports
    supported_markets = Column(JSON, default=list)

    # Description / notes
    description = Column(Text, nullable=True)

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("key", name="uq_model_metadata_key"),
    )


class AIPredictionAudit(Base):
    """
    E4 — AI Audit Log

    One row per ensemble prediction call.
    Stores the complete per-model breakdown so validators and admins can
    inspect exactly how the final probability was reached.
    """
    __tablename__ = "ai_prediction_audit"

    id          = Column(Integer, primary_key=True, index=True)
    match_id    = Column(String(128), nullable=False, index=True)  # external or internal
    home_team   = Column(String(128), nullable=True)
    away_team   = Column(String(128), nullable=True)

    # Final ensemble output
    home_prob   = Column(Float, nullable=False)
    draw_prob   = Column(Float, nullable=False)
    away_prob   = Column(Float, nullable=False)
    over_25_prob = Column(Float, nullable=True)
    btts_prob   = Column(Float, nullable=True)
    confidence  = Column(Float, nullable=True)
    risk_score  = Column(Float, nullable=True)   # entropy of final distribution
    model_agreement = Column(Float, nullable=True)  # % models within ±5% of ensemble

    # Per-model breakdown (list of dicts)
    individual_results = Column(JSON, nullable=True)

    # Weights snapshot at prediction time
    weights_snapshot = Column(JSON, nullable=True)

    # Models with pkl loaded at prediction time
    pkl_models_active = Column(Integer, default=0)

    # Caller context
    triggered_by = Column(String(64), default="api")  # api / validator / auto

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
