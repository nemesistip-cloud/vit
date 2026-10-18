"""VITPredict-owned match and prediction persistence models.

These models retain the existing table names and columns. ``app.db.models``
re-exports them so current imports and migrations remain compatible.
"""

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(String(36), ForeignKey("markets.id"), nullable=True)
    market_type = Column(String(20), default="sports", nullable=False, index=True)
    external_id = Column(String, unique=True, nullable=True, index=True)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    league = Column(String, nullable=False)
    kickoff_time = Column(DateTime, nullable=False)
    status = Column(String, default="scheduled")
    sport = Column(String(32), default="football", nullable=True, index=True)
    source = Column(String(32), default="unknown", index=True)
    fingerprint = Column(String(255), nullable=True, index=True)
    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)
    actual_outcome = Column(String, nullable=True)
    statistics = Column(JSON, nullable=True)
    opening_odds_home = Column(Float, nullable=True)
    opening_odds_draw = Column(Float, nullable=True)
    opening_odds_away = Column(Float, nullable=True)
    closing_odds_home = Column(Float, nullable=True)
    closing_odds_draw = Column(Float, nullable=True)
    closing_odds_away = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    predictions = relationship("Prediction", back_populates="match", uselist=True)
    clv_entries = relationship("CLVEntry", back_populates="match")
    market = relationship("Market", back_populates="matches")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)
    market_id = Column(String(36), ForeignKey("markets.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    request_hash = Column(String, unique=True, nullable=True, index=True)
    home_prob = Column(Float, nullable=False)
    draw_prob = Column(Float, nullable=False)
    away_prob = Column(Float, nullable=False)
    over_25_prob = Column(Float, nullable=True)
    under_25_prob = Column(Float, nullable=True)
    btts_prob = Column(Float, nullable=True)
    no_btts_prob = Column(Float, nullable=True)
    ah_line = Column(Float, nullable=True)
    ah_home_prob = Column(Float, nullable=True)
    ah_away_prob = Column(Float, nullable=True)
    ah_lines = Column(JSON, nullable=True)
    cs_probs = Column(JSON, nullable=True)
    top_correct_score = Column(String(8), nullable=True)
    top_cs_prob = Column(Float, nullable=True)
    model_consensus = Column(JSON, nullable=True)
    alternative_bets = Column(JSON, nullable=True)
    status = Column(String(32), nullable=False, default="READY", server_default="READY", index=True)
    source = Column(String(32), nullable=False, default="live_generated", server_default="live_generated")
    is_seed = Column(Boolean, nullable=False, default=False, server_default="false")
    provenance = Column(JSON, nullable=True)
    job_id = Column(String(64), nullable=True)
    error_message = Column(String, nullable=True)
    consensus_prob = Column(Float)
    final_ev = Column(Float)
    recommended_stake = Column(Float)
    model_weights = Column(JSON)
    model_insights = Column(JSON, nullable=True)
    confidence = Column(Float)
    bet_side = Column(String, nullable=True)
    entry_odds = Column(Float)
    raw_edge = Column(Float)
    normalized_edge = Column(Float)
    vig_free_edge = Column(Float)
    submitted_market_id = Column(String, nullable=True)
    submitted_market_side = Column(String, nullable=True)
    submitted_stake = Column(Float, nullable=True)
    was_correct = Column(Boolean, nullable=True)
    settled_profit = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("home_prob >= 0 AND home_prob <= 1", name="check_home_prob"),
        CheckConstraint("draw_prob >= 0 AND draw_prob <= 1", name="check_draw_prob"),
        CheckConstraint("away_prob >= 0 AND away_prob <= 1", name="check_away_prob"),
        CheckConstraint("recommended_stake >= 0 AND recommended_stake <= 0.20", name="check_stake_limit"),
    )

    match = relationship("Match", back_populates="predictions")