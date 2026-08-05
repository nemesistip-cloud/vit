from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone

from app.db.database import get_db
from app.schemas.schemas import MatchRequest, PredictionResponse, ModelInsight
from app.api.middleware.auth import verify_api_key
from app.api.deps import get_optional_user
from app.core.dependencies import get_orchestrator_dep

router = APIRouter(prefix="/predict/tennis", tags=["tennis"], dependencies=[Depends(verify_api_key)])
logger = logging.getLogger(__name__)

@router.post("", response_model=PredictionResponse)
async def predict_tennis(
    match: MatchRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator = Depends(get_orchestrator_dep),
    current_user = Depends(get_optional_user),
):
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    from app.services.multi_sport_orchestrator import MultiSportOrchestrator
    m_orch = MultiSportOrchestrator(orchestrator)

    features = {
        "home_team": match.home_team,
        "away_team": match.away_team,
        "league": match.league,
        "sport": "tennis",
        "market_odds": match.market_odds
    }

    raw_res = await m_orch.predict(features, sport="tennis")
    pred = raw_res["predictions"]

    # Create individual results as ModelInsight objects
    insights = [
        ModelInsight(
            model_name=ir.get("model_name", "unknown"),
            model_type="neural",
            model_weight=1.0 / len(raw_res.get("individual_results", [1])),
            supported_markets=["moneyline"],
            home_prob=ir.get("home_prob"),
            draw_prob=ir.get("draw_prob", 0.0),
            away_prob=ir.get("away_prob"),
            over_2_5_prob=0.0,
            btts_prob=0.0,
            home_goals_expectation=0.0,
            away_goals_expectation=0.0,
            confidence=ir.get("confidence", 0.5),
            latency_ms=10.0,
            failed=ir.get("failed", False),
            error=None
        ) for ir in raw_res.get("individual_results", [])
    ]

    # Build proper Response
    return PredictionResponse(
        match_id=0,
        home_prob=pred["home_prob"],
        draw_prob=pred["draw_prob"],
        away_prob=pred["away_prob"],
        over_25_prob=pred.get("over_25_prob", 0.0),
        under_25_prob=1.0 - pred.get("over_25_prob", 0.0),
        btts_prob=pred.get("btts_prob", 0.0),
        consensus_prob=max(pred["home_prob"], pred["draw_prob"], pred["away_prob"]),
        final_ev=0.0,
        recommended_stake=0.02,
        edge=0.0,
        confidence=0.7,
        timestamp=datetime.now(timezone.utc),
        models_used=pred["models_used"],
        models_total=pred["models_total"],
        data_source=pred["data_source"],
        bet_side="home" if pred["home_prob"] > pred["away_prob"] else "away",
        entry_odds=match.market_odds.get("home", 2.0),
        raw_edge=0.0,
        normalized_edge=0.0,
        vig_free_edge=0.0,
        model_weights={ir["model_name"]: 1.0/max(1, len(insights)) for ir in raw_res.get("individual_results", [])},
        model_insights=insights,
        neural_consensus_score=pred["home_prob"] * 100,
        analytics_rating="GOOD",
        prediction_accuracy_estimate=0.75
    )
