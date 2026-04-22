# app/schemas/schemas.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Any, Optional, Dict, List, Tuple, Union


# --- INPUT ---
class MatchRequest(BaseModel):
    home_team: str
    away_team: str
    league: str
    kickoff_time: datetime
    market_odds: Dict[str, float] = Field(default_factory=dict)
    fixture_id: Optional[str] = None  # Unique fixture ID from Football-Data API


class ResultUpdate(BaseModel):
    home_goals: int = Field(..., ge=0, description="Home team goals (must be 0 or more)")
    away_goals: int = Field(..., ge=0, description="Away team goals (must be 0 or more)")
    closing_odds_home: float = Field(..., gt=1.0, description="Closing home odds (must be > 1.0)")
    closing_odds_draw: float = Field(..., gt=1.0, description="Closing draw odds (must be > 1.0)")
    closing_odds_away: float = Field(..., gt=1.0, description="Closing away odds (must be > 1.0)")


# --- OUTPUT ---
class ModelInsight(BaseModel):
    model_name: str
    model_type: str
    model_weight: float
    supported_markets: List[str]
    home_prob: Optional[float]
    draw_prob: Optional[float]
    away_prob: Optional[float]
    over_2_5_prob: Optional[float]
    btts_prob: Optional[float]
    home_goals_expectation: Optional[float]
    away_goals_expectation: Optional[float]
    confidence: Union[float, Dict[str, float]]
    confidence_breakdown: Optional[Dict[str, float]] = None
    latency_ms: Optional[float]
    failed: bool
    error: Optional[str]
    calibration: Optional[Dict[str, Any]] = None


class PredictionResponse(BaseModel):
    match_id: int
    home_prob: float
    draw_prob: float
    away_prob: float
    over_25_prob: Optional[float]
    under_25_prob: Optional[float]
    btts_prob: Optional[float]
    consensus_prob: float
    final_ev: float
    recommended_stake: float
    edge: float
    confidence: float
    timestamp: datetime
    
    # Enhanced Intelligence Data
    models_used: int
    models_total: int
    data_source: str
    bet_side: Optional[str]
    entry_odds: Optional[float]
    raw_edge: Optional[float]
    normalized_edge: Optional[float]
    vig_free_edge: Optional[float]
    model_weights: Dict[str, float]
    model_insights: List[ModelInsight]
    neural_consensus_score: float
    intelligence_rating: str
    prediction_accuracy_estimate: float

    # v4.10.0 — explicit fallback / data-quality surfacing.
    # Lets the frontend (and operators) tell at a glance whether this
    # prediction came from real data + real models, or whether any path
    # had to degrade. Every flag here corresponds to a logged WARNING.
    data_quality: Optional[Dict[str, Any]] = None


class CLVResponse(BaseModel):
    match_id: int
    bet_side: str
    entry_odds: float
    closing_odds: Optional[float]
    clv: Optional[float]
    profit: Optional[float]
    bet_outcome: Optional[str]


class EdgeResponse(BaseModel):
    edge_id: str
    description: str
    roi: float
    sample_size: int
    confidence: float
    status: str


class HealthResponse(BaseModel):
    status: str
    models_loaded: int
    db_connected: bool
    clv_tracking_enabled: bool


class HistoryResponse(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    consensus_prob: float
    final_ev: float
    recommended_stake: float
    actual_outcome: Optional[str]
    clv: Optional[float]
    timestamp: datetime


# --- HELPER FUNCTIONS ---
def calculate_true_probabilities(
    home_odds: float,
    draw_odds: float,
    away_odds: float
) -> Tuple[float, float, float]:
    """
    Calculate true probabilities by removing bookmaker margin.

    Args:
        home_odds: Decimal odds for home win
        draw_odds: Decimal odds for draw
        away_odds: Decimal odds for away win

    Returns:
        (true_home_prob, true_draw_prob, true_away_prob) that sum to 1.0
    """
    if home_odds <= 0 or draw_odds <= 0 or away_odds <= 0:
        return 0.33, 0.34, 0.33

    implied_home = 1 / home_odds
    implied_draw = 1 / draw_odds
    implied_away = 1 / away_odds

    total_implied = implied_home + implied_draw + implied_away

    if total_implied <= 0:
        return 0.33, 0.34, 0.33

    true_home = implied_home / total_implied
    true_draw = implied_draw / total_implied
    true_away = implied_away / total_implied

    return true_home, true_draw, true_away