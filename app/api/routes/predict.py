from app.core.markets import get_markets_for_sport
# app/api/routes/predict.py
# VIT Sports Intelligence Network — v2.1.0
# Native AI Only version

import hashlib
import json
import logging
import math
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timezone

from app.config import APP_VERSION, MAX_STAKE, MIN_EDGE_THRESHOLD, MAX_PREDICTIONS_PER_DAY, PUBLIC_APP_URL
from app.db.database import get_db
from app.db.models import Match, Prediction
from app.schemas.schemas import MatchRequest, PredictionResponse
from app.services.clv_tracker import CLVTracker
from app.services.market_utils import MarketUtils
from app.api.middleware.auth import verify_api_key
from app.api.deps import get_optional_user
from app.services.alerts import BetAlert
from app.core.dependencies import get_orchestrator_dep, get_telegram_dep

from app.tasks.clv import update_clv_task
from app.tasks.edges import recalculate_edges_task
from app.services.decision_logger import DecisionLogger
from app.services.predict_features import build_predict_features

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/predict",
    tags=["predictions"],
    dependencies=[Depends(verify_api_key)]
)

VERSION = APP_VERSION

def to_naive_utc(dt_input) -> datetime:
    if isinstance(dt_input, str):
        try:
            parsed = datetime.fromisoformat(dt_input.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=None)
        except Exception as e:
            logger.warning(f"Failed to parse kickoff_time '{dt_input}': {e}")
            return datetime.now(timezone.utc).replace(tzinfo=None)
    elif isinstance(dt_input, datetime):
        if dt_input.tzinfo is not None:
            return dt_input.astimezone(timezone.utc).replace(tzinfo=None)
        return dt_input
    return datetime.now(timezone.utc).replace(tzinfo=None)

def create_idempotency_key(match: MatchRequest, user_id: Optional[int] = None) -> str:
    odds = match.market_odds or {}
    odds_sig = {k: round(float(v), 2) for k, v in odds.items() if v}
    kt = match.kickoff_time
    kickoff_bucket = kt.replace(minute=(kt.minute // 30) * 30, second=0, microsecond=0)
    content = {
        "home_team":    match.home_team,
        "away_team":    match.away_team,
        "kickoff_time": kickoff_bucket.isoformat(),
        "league":       match.league,
        "odds_sig":     odds_sig,
        "user_id":      user_id,
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:32]

def _argmax_side(hp: float, dp: float, ap: float) -> str:
    return max((("home", hp), ("draw", dp), ("away", ap)), key=lambda x: x[1])[0]

def _entropy_confidence(hp: float, dp: float, ap: float) -> float:
    probs = [p for p in (hp, dp, ap) if p > 0]
    if not probs: return 0.50
    ent = -sum(p * math.log(p) for p in probs); max_ent = math.log(3); normalised = max(0.0, min(1.0, 1.0 - (ent / max_ent)))
    return round(0.50 + normalised * 0.45, 3)

def build_prediction_response(prediction: Prediction, match: Match, orchestrator: Optional[object] = None, sport: str = "football", available_markets: list[str] = None, data_quality: Optional[dict] = None, data_source: str = "native_ensemble") -> PredictionResponse:
    conf = prediction.confidence
    rating = "EXCELLENT" if conf >= 0.80 else ("VERY GOOD" if conf >= 0.72 else ("GOOD" if conf >= 0.63 else ("FAIR" if conf >= 0.55 else "POOR")))
    accuracy = round(min(82.0, max(54.0, 44.0 + conf * 50.0)), 1)
    return PredictionResponse(
        match_id=prediction.match_id, sport=sport, available_markets=available_markets or [],
        home_prob=prediction.home_prob, draw_prob=prediction.draw_prob, away_prob=prediction.away_prob,
        over_25_prob=prediction.over_25_prob, under_25_prob=prediction.under_25_prob, btts_prob=prediction.btts_prob,
        model_consensus=prediction.model_consensus, alternative_bets=prediction.alternative_bets, consensus_prob=prediction.consensus_prob,
        final_ev=prediction.final_ev, recommended_stake=prediction.recommended_stake, edge=prediction.vig_free_edge, confidence=prediction.confidence, timestamp=prediction.timestamp,
        models_used=len(prediction.model_insights) if prediction.model_insights else 0,
        models_total=13,
        data_source=data_source, bet_side=prediction.bet_side, entry_odds=prediction.entry_odds, raw_edge=prediction.raw_edge, normalized_edge=prediction.normalized_edge, vig_free_edge=prediction.vig_free_edge,
        model_weights=prediction.model_weights or {}, model_insights=prediction.model_insights or [], neural_consensus_score=(prediction.consensus_prob * 100), intelligence_rating=rating, prediction_accuracy_estimate=accuracy, data_quality=data_quality
    )

@router.post("", response_model=PredictionResponse)
async def predict(match: MatchRequest, db: AsyncSession = Depends(get_db), orchestrator = Depends(get_orchestrator_dep), telegram_alerts = Depends(get_telegram_dep), current_user = Depends(get_optional_user)):
    if orchestrator is None: raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    user_id = current_user.id if current_user else None; sport = (match.sport or "football").lower(); available_markets = get_markets_for_sport(sport)
    idempotency_key = create_idempotency_key(match, user_id); naive_kickoff = to_naive_utc(match.kickoff_time)

    existing = await db.execute(select(Prediction).where(Prediction.request_hash == idempotency_key))
    existing_pred = existing.scalar_one_or_none()
    if existing_pred:
        m = (await db.execute(select(Match).where(Match.id == existing_pred.match_id))).scalar_one_or_none()
        if m: return build_prediction_response(existing_pred, m, orchestrator, sport=sport, available_markets=available_markets)

    db_match = (await db.execute(select(Match).where(Match.home_team == match.home_team, Match.away_team == match.away_team, Match.kickoff_time == naive_kickoff))).scalar_one_or_none()
    if not db_match:
        db_match = Match(home_team=match.home_team, away_team=match.away_team, league=match.league, kickoff_time=naive_kickoff, source="predict", sport=sport)
        db.add(db_match); await db.flush()

    match_features = await build_predict_features(db, match.home_team, match.away_team, match.league)
    features = {"home_team": match.home_team, "away_team": match.away_team, "league": match.league, "market_odds": match.market_odds, "match_features": match_features}
    raw_result = await orchestrator.predict(features, idempotency_key, sport=sport)
    pred_data = raw_result.get("predictions", raw_result)

    hp, dp, ap = float(pred_data["home_prob"]), float(pred_data["draw_prob"]), float(pred_data["away_prob"])
    odds = match.market_odds; h_odds, d_odds, a_odds = float(odds.get("home", 2.0)), float(odds.get("draw", 3.0)), float(odds.get("away", 3.0))
    best_bet = MarketUtils.determine_best_bet(hp, dp, ap, h_odds, d_odds, a_odds)

    prediction = Prediction(
        request_hash=idempotency_key, match_id=db_match.id, user_id=user_id, home_prob=hp, draw_prob=dp, away_prob=ap,
        confidence=_entropy_confidence(hp, dp, ap), bet_side=best_bet.get("best_side"), entry_odds=best_bet.get("odds"),
        vig_free_edge=best_bet.get("edge", 0), model_insights=raw_result.get("individual_results", []), consensus_prob=hp if best_bet.get("best_side") == "home" else (ap if best_bet.get("best_side") == "away" else dp)
    )
    db.add(prediction); await db.commit(); await db.refresh(prediction)
    return build_prediction_response(prediction, db_match, orchestrator, sport=sport, available_markets=available_markets)

@router.get("/{match_id}/insights")
async def get_match_insights(match_id: int, db: AsyncSession = Depends(get_db)):
    m = (await db.execute(select(Match).where(Match.id == match_id))).scalar_one_or_none()
    p = (await db.execute(select(Prediction).where(Prediction.match_id == match_id).order_by(desc(Prediction.timestamp)).limit(1))).scalar_one_or_none()
    if not m or not p: raise HTTPException(status_code=404, detail="Not found")

    insight = {
        "summary": f"Native analysis for {m.home_team} vs {m.away_team}. Confidence {p.confidence*100:.1f}%.",
        "key_factors": [f"Home Win: {p.home_prob*100:.1f}%", f"Edge detected: {p.vig_free_edge*100:.2f}%"],
        "recommendation": f"Back {p.bet_side} @ {p.entry_odds}",
        "confidence": float(p.confidence),
        "provider": "native_ensemble"
    }
    return {"match_id": match_id, "native": insight, "source": "native"}
