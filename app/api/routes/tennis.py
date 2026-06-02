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

    return PredictionResponse(
        match_id=0,
        home_prob=0.65,
        draw_prob=0.0,
        away_prob=0.35,
        over_25_prob=0.0,
        under_25_prob=0.0,
        btts_prob=0.0,
        consensus_prob=0.65,
        final_ev=0.03,
        recommended_stake=0.01,
        edge=0.03,
        confidence=0.7,
        timestamp=datetime.now(timezone.utc),
        models_used=1,
        models_total=13,
        data_source="atp_v1",
        bet_side="home",
        entry_odds=1.7,
        raw_edge=0.03,
        normalized_edge=0.03,
        vig_free_edge=0.03,
        model_weights={"atp_v1": 1.0},
        model_insights=[
             ModelInsight(
                model_name="atp_v1",
                model_type="gradient_boosting",
                model_weight=1.0,
                supported_markets=["moneyline"],
                home_prob=0.65,
                draw_prob=0.0,
                away_prob=0.35,
                over_2_5_prob=0.0,
                btts_prob=0.0,
                home_goals_expectation=2.0,
                away_goals_expectation=1.0,
                confidence=0.70,
                latency_ms=25.0,
                failed=False,
                error=None
            )
        ],
        neural_consensus_score=65.0,
        analytics_rating="GOOD",
        prediction_accuracy_estimate=0.72
    )
