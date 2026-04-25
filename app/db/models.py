# app/db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON, Text, Index, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, nullable=True, index=True)  # For API integration
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    league = Column(String, nullable=False)
    kickoff_time = Column(DateTime, nullable=False)
    status = Column(String, default="scheduled")

    # Provenance: where this fixture came from
    # values: manual_upload | footballdata | odds_api | sportmonks | api_football
    #         | user_csv | seed | synthetic | unknown
    source = Column(String(32), default="unknown", index=True)
    # Stable fingerprint for cross-source dedup: lowercase normalized
    # "{date}::{home}::{away}::{league}"
    fingerprint = Column(String(255), nullable=True, index=True)

    # Actual results (filled post-match)
    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)
    actual_outcome = Column(String, nullable=True)  # home/draw/away

    # Market data
    opening_odds_home = Column(Float, nullable=True)
    opening_odds_draw = Column(Float, nullable=True)
    opening_odds_away = Column(Float, nullable=True)
    closing_odds_home = Column(Float, nullable=True)
    closing_odds_draw = Column(Float, nullable=True)
    closing_odds_away = Column(Float, nullable=True)

    # Timestamps (with timezone - for system operations)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    predictions = relationship("Prediction", back_populates="match", uselist=True)
    clv_entries = relationship("CLVEntry", back_populates="match")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    request_hash = Column(String, unique=True, nullable=True, index=True)

    # Multi-market predictions
    home_prob = Column(Float, nullable=False)
    draw_prob = Column(Float, nullable=False)
    away_prob = Column(Float, nullable=False)
    over_25_prob = Column(Float, nullable=True)
    under_25_prob = Column(Float, nullable=True)
    btts_prob = Column(Float, nullable=True)
    no_btts_prob = Column(Float, nullable=True)

    # Metadata
    consensus_prob = Column(Float)
    final_ev = Column(Float)
    recommended_stake = Column(Float)
    model_weights = Column(JSON)
    model_insights = Column(JSON, nullable=True)
    confidence = Column(Float)

    # Market comparison
    bet_side = Column(String, nullable=True)  # home/draw/away - which side was bet
    entry_odds = Column(Float)  # Odds when prediction was made
    raw_edge = Column(Float)  # model_prob - market_prob (unadjusted)
    normalized_edge = Column(Float)  # After removing bookmaker margin
    vig_free_edge = Column(Float)  # True edge after vig removal

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint('home_prob >= 0 AND home_prob <= 1', name='check_home_prob'),
        CheckConstraint('draw_prob >= 0 AND draw_prob <= 1', name='check_draw_prob'),
        CheckConstraint('away_prob >= 0 AND away_prob <= 1', name='check_away_prob'),
        CheckConstraint('recommended_stake >= 0 AND recommended_stake <= 0.20', name='check_stake_limit'),
    )

    match = relationship("Match", back_populates="predictions")


class CLVEntry(Base):
    """Closing Line Value tracking - the truth metric"""
    __tablename__ = "clv_entries"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    prediction_id = Column(Integer, ForeignKey("predictions.id"))

    bet_side = Column(String, nullable=False)  # home/draw/away - CRITICAL for accurate CLV
    entry_odds = Column(Float, nullable=False)
    closing_odds = Column(Float, nullable=True)
    clv = Column(Float, nullable=True)  # (entry - closing) / closing

    bet_outcome = Column(String, nullable=True)  # win/loss/pending
    profit = Column(Float, nullable=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    match = relationship("Match", back_populates="clv_entries")


class Edge(Base):
    """Edge database - profitable patterns"""
    __tablename__ = "edges"

    id = Column(Integer, primary_key=True, index=True)
    edge_id = Column(String, unique=True, nullable=False)
    description = Column(String)

    # Performance metrics
    roi = Column(Float, default=0.0)
    sample_size = Column(Integer, default=0)
    confidence = Column(Float, default=0.0)
    avg_edge = Column(Float, default=0.0)

    # Filters that define this edge
    league = Column(String, nullable=True)
    home_condition = Column(String, nullable=True)
    away_condition = Column(String, nullable=True)
    market = Column(String, default="1x2")

    # Lifecycle
    status = Column(String, default="active")  # active, declining, dead, revived
    decay_rate = Column(Float, default=0.02)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    archived_at = Column(DateTime(timezone=True), nullable=True)


class ModelPerformance(Base):
    __tablename__ = "model_performances"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, unique=True, nullable=False)
    model_type = Column(String, nullable=False)
    version = Column(Integer, default=1)

    weight_decay_rate = Column(Float, default=0.05)
    min_weight_threshold = Column(Float, default=0.05)
    performance_window = Column(Integer, default=100)
    last_weight_update = Column(DateTime(timezone=True), nullable=True)
    consecutive_underperforming = Column(Integer, default=0)

    # Performance metrics
    accuracy_score = Column(Float)
    current_weight = Column(Float, default=1.0)
    calibration_error = Column(Float)
    expected_value = Column(Float)
    sharpe_ratio = Column(Float)
    positive_clv_rate = Column(Float, default=0.0)  # Track CLV by model

    # Certification
    certified = Column(Boolean, default=False)
    final_score = Column(Float, nullable=True)
    last_certified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BankrollState(Base):
    """Persists bankroll snapshots for recovery across restarts."""
    __tablename__ = "bankroll_states"

    id = Column(Integer, primary_key=True, index=True)
    initial_balance = Column(Float, default=10000.0)
    current_balance = Column(Float, default=10000.0)
    peak_balance = Column(Float, default=10000.0)
    total_staked = Column(Float, default=0.0)
    total_profit = Column(Float, default=0.0)
    total_bets = Column(Integer, default=0)
    winning_bets = Column(Integer, default=0)
    losing_bets = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DecisionLog(Base):
    """Full audit trail of every betting decision made by the system."""
    __tablename__ = "decision_logs"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, nullable=True, index=True)
    prediction_id = Column(Integer, nullable=True, index=True)
    decision_type = Column(String, default="bet")
    stake = Column(Float, nullable=True)
    odds = Column(Float, nullable=True)
    edge = Column(Float, nullable=True)
    reason = Column(String, nullable=True)
    model_contributions = Column(Text, nullable=True)
    market_context = Column(Text, nullable=True)
    bankroll_state = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class Team(Base):
    """Team registry for cross-source ID mapping and name normalisation."""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, nullable=True, index=True)
    name = Column(String, nullable=False, index=True)
    league = Column(String, nullable=True)
    country = Column(String, nullable=True)
    short_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AIPrediction(Base):
    """Store manually ingested AI predictions"""
    __tablename__ = "ai_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    source = Column(String(50), nullable=False)  # chatgpt, gemini, grok, deepseek, perplexity
    home_prob = Column(Float, nullable=False)
    draw_prob = Column(Float, nullable=False)
    away_prob = Column(Float, nullable=False)
    confidence = Column(Float, default=0.7)
    reason = Column(String(500), nullable=True)
    model_version = Column(String(50), default="manual_v1")
    is_certified = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Performance tracking (filled after match completes)
    was_correct = Column(Boolean, nullable=True)
    calibration_error = Column(Float, nullable=True)
    
    __table_args__ = (
        Index('idx_ai_match_source', 'match_id', 'source'),
        Index('idx_ai_timestamp', 'timestamp'),
    )


class AIPerformance(Base):
    """Track performance per AI for dynamic weighting"""
    __tablename__ = "ai_performances"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), unique=True, nullable=False)
    
    # Overall metrics
    accuracy = Column(Float, default=0.0)
    calibration_score = Column(Float, default=0.0)
    sample_size = Column(Integer, default=0)
    
    # Bias detection
    bias_home_overrate = Column(Float, default=0.0)   # positive = overrates home
    bias_draw_overrate = Column(Float, default=0.0)
    bias_away_overrate = Column(Float, default=0.0)
    
    # League-specific (JSON)
    league_accuracy = Column(JSON, default={})
    
    # Dynamic weight
    current_weight = Column(Float, default=1.0)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata
    total_predictions = Column(Integer, default=0)
    certified = Column(Boolean, default=False)


class AISignalCache(Base):
    """Pre-computed AI signals for each match (for fast inference)"""
    __tablename__ = "ai_signal_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), unique=True, nullable=False)
    
    # Consensus signals
    consensus_home = Column(Float, nullable=False)
    consensus_draw = Column(Float, nullable=False)
    consensus_away = Column(Float, nullable=False)
    disagreement_score = Column(Float, nullable=False)  # variance
    max_confidence = Column(Float, nullable=False)
    weighted_home = Column(Float, nullable=False)
    weighted_draw = Column(Float, nullable=False)
    weighted_away = Column(Float, nullable=False)
    
    # Per-AI signals (JSON for flexibility)
    per_ai_predictions = Column(JSON, default={})
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class SubscriptionPlan(Base):
    """Subscription plan definitions"""
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # free, pro, elite
    display_name = Column(String(100), nullable=False)
    price_monthly = Column(Float, default=0.0)
    price_yearly = Column(Float, default=0.0)
    features = Column(JSON, default={})
    prediction_limit = Column(Integer, nullable=True)  # None = unlimited
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserSubscription(Base):
    """Track user subscription state (keyed by API key hash)"""
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    api_key_hash = Column(String(64), unique=True, nullable=False, index=True)
    plan_name = Column(String(50), default="free", nullable=False)
    status = Column(String(20), default="active")  # active, cancelled, past_due
    stripe_customer_id = Column(String(100), nullable=True)
    stripe_subscription_id = Column(String(100), nullable=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    prediction_count_today = Column(Integer, default=0)
    prediction_count_reset_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AuditLog(Base):
    """Admin audit trail — every significant action"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), nullable=False)
    actor = Column(String(100), default="system")  # api_key hash or 'system'
    resource = Column(String(100), nullable=True)   # e.g. 'prediction', 'training'
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    status = Column(String(20), default="success")  # success, failure, warning
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_audit_action', 'action'),
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_actor', 'actor'),
    )


class TrainingDataset(Base):
    """Records of uploaded training datasets"""
    __tablename__ = "training_datasets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    format = Column(String(10), nullable=False)  # csv, json
    record_count = Column(Integer, default=0)
    leagues = Column(JSON, default=[])
    date_range_start = Column(String(20), nullable=True)
    date_range_end = Column(String(20), nullable=True)
    status = Column(String(20), default="pending")  # pending, processed, error
    error_message = Column(Text, nullable=True)
    uploaded_by = Column(String(100), default="admin")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)


class User(Base):
    """Registered user — supports JWT authentication + RBAC"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user")  # user, admin, validator
    # RBAC extensions
    admin_role = Column(String(20), nullable=True)          # super_admin, admin, auditor, support
    subscription_tier = Column(String(20), default="viewer") # viewer, analyst, pro, elite
    is_banned = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    # KYC fields
    kyc_status = Column(String(20), default="none")   # none, pending, approved, rejected
    kyc_submitted_at = Column(DateTime(timezone=True), nullable=True)
    kyc_data = Column(JSON, nullable=True)
    # Gamification
    current_streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    total_xp = Column(Integer, default=0)

    # Wallet module relationships (back_populates wired in app/modules/wallet/models.py)
    wallet = relationship("Wallet", back_populates=None, uselist=False, viewonly=True)
    wallet_transactions = relationship("WalletTransaction", foreign_keys="WalletTransaction.user_id", viewonly=True)

    # Notification module relationships (Module K)
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    notification_preferences = relationship("NotificationPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Trust module relationships (Module I)
    trust_score = relationship("UserTrustScore", foreign_keys="UserTrustScore.user_id", uselist=False, viewonly=True)
    fraud_flags = relationship("FraudFlag", foreign_keys="FraudFlag.user_id", viewonly=True)
    risk_events = relationship("RiskEvent", foreign_keys="RiskEvent.user_id", viewonly=True)

    # Task module relationships (Module T)
    task_completions = relationship("UserTaskCompletion", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_role', 'role'),
    )


class TrainingJob(Base):
    """Persisted training job records (Module D)"""
    __tablename__ = "training_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(20), default="queued")  # queued, running, completed, failed
    config = Column(JSON, nullable=True)
    results = Column(JSON, nullable=True)
    summary = Column(JSON, nullable=True)
    events = Column(JSON, nullable=True)          # persisted event log for SSE replay
    progress_pct = Column(Float, default=0.0)     # 0-100, updated per-model
    current_model = Column(String(200), nullable=True)  # model being trained right now
    total_models = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)   # set when status=failed
    data_quality_score = Column(Float, nullable=True)
    training_prompt = Column(Text, nullable=True)
    created_by = Column(String(100), default="system")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    steps = relationship("TrainingGuideStep", back_populates="job")

    __table_args__ = (
        Index('idx_training_jobs_status', 'status'),
    )


class TrainingGuideStep(Base):
    """Step-by-step training guide generated per job (Module D)"""
    __tablename__ = "training_guide_steps"

    id = Column(Integer, primary_key=True, index=True)
    job_id_fk = Column(Integer, ForeignKey("training_jobs.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    step_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending, done, skipped
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("TrainingJob", back_populates="steps")


# Indexes for performance
Index('idx_matches_kickoff', Match.kickoff_time)
Index('idx_matches_status', Match.status)
Index('idx_predictions_timestamp', Prediction.timestamp.desc())
Index('idx_predictions_match_id', Prediction.match_id)
Index('idx_clv_match', CLVEntry.match_id)
Index('idx_clv_bet_side', CLVEntry.bet_side)
Index('idx_edges_status', Edge.status)
Index('idx_edges_roi', Edge.roi.desc())
Index('idx_model_perf_certified', ModelPerformance.certified)
Index('idx_decision_logs_match', DecisionLog.match_id)
Index('idx_teams_external_id', Team.external_id)
Index('idx_teams_name', Team.name)
Index('idx_ai_predictions_match', AIPrediction.match_id)
Index('idx_ai_predictions_source', AIPrediction.source)
Index('idx_ai_signal_cache_match', AISignalCache.match_id)
