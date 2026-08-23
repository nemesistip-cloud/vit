"""
Recommendation Engine API Routes (Phase B)

Exposes endpoints for market-aware prediction recommendations, composite signal scoring,
ensemble model consensus metrics, probability calibration, qualified signal states,
and historical signal performance tracking.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.database import get_db
from app.db.models import Match, Prediction
from app.services.recommendation_engine import (
    RecommendationEngine,
    STATE_QUALIFIED_SIGNAL,
    STATE_LOW_CONFIDENCE,
    STATE_HIGH_DISAGREEMENT,
    STATE_DATA_DEFICIENT,
    STATE_NO_SIGNAL,
)
from app.api.deps import get_optional_user
from app.api.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


class RecommendationEvaluateRequest(BaseModel):
    match_id: Optional[int] = None
    home_team: str
    away_team: str
    market_type: str = Field(default="sports", description="sports | niche")
    category: str = Field(default="football", description="football | basketball | election | governance | merit")
    home_prob: float = Field(default=0.333, ge=0.0, le=1.0)
    draw_prob: float = Field(default=0.333, ge=0.0, le=1.0)
    away_prob: float = Field(default=0.334, ge=0.0, le=1.0)
    market_odds: Optional[Dict[str, float]] = Field(default_factory=dict)
    individual_results: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    feature_completeness: float = Field(default=1.0, ge=0.0, le=1.0)
    save_to_history: bool = True


class BatchEvaluateRequest(BaseModel):
    matches: List[RecommendationEvaluateRequest]


@router.post("/evaluate")
async def evaluate_recommendation(
    req: RecommendationEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_optional_user),
):
    """
    Generate a market-aware recommendation, composite signal score,
    model consensus breakdown, calibration status, and qualification state.
    """
    engine = RecommendationEngine(db=db)
    rec = engine.generate_recommendation(
        match_id=req.match_id,
        home_team=req.home_team,
        away_team=req.away_team,
        market_type=req.market_type,
        category=req.category,
        home_prob=req.home_prob,
        draw_prob=req.draw_prob,
        away_prob=req.away_prob,
        market_odds=req.market_odds,
        individual_results=req.individual_results,
        feature_completeness=req.feature_completeness,
    )

    if req.match_id and req.save_to_history:
        await engine.save_signal_history(req.match_id, rec)

    return rec


@router.get("/signals/{match_id}")
async def get_match_signal(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_optional_user),
):
    """
    Fetch recommendation & signal metrics for a given match.
    """
    match_stmt = select(Match).where(Match.id == match_id)
    match_res = await db.execute(match_stmt)
    match = match_res.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    pred_stmt = select(Prediction).where(Prediction.match_id == match_id).order_by(desc(Prediction.timestamp)).limit(1)
    pred_res = await db.execute(pred_stmt)
    pred = pred_res.scalar_one_or_none()

    hp = float(pred.home_prob or 0.333) if pred else 0.333
    dp = float(pred.draw_prob or 0.333) if pred else 0.333
    ap = float(pred.away_prob or 0.334) if pred else 0.334

    market_odds = {
        "home": match.opening_odds_home or 2.5,
        "draw": match.opening_odds_draw or 3.2,
        "away": match.opening_odds_away or 2.8,
    }

    individual_results = pred.model_insights if pred and isinstance(pred.model_insights, list) else []

    engine = RecommendationEngine(db=db)
    rec = engine.generate_recommendation(
        match_id=match.id,
        home_team=match.home_team,
        away_team=match.away_team,
        market_type=match.market_type or "sports",
        category=match.sport or "football",
        home_prob=hp,
        draw_prob=dp,
        away_prob=ap,
        market_odds=market_odds,
        individual_results=individual_results,
    )

    return rec


@router.get("/history")
async def get_signal_history(
    signal_state: Optional[str] = Query(None, description="QUALIFIED_SIGNAL | LOW_CONFIDENCE | HIGH_DISAGREEMENT | DATA_DEFICIENT | NO_SIGNAL"),
    market_type: Optional[str] = Query(None, description="sports | niche"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_optional_user),
):
    """
    Fetch historical signal tracking records and accuracy performance.
    """
    engine = RecommendationEngine(db=db)
    signals = await engine.get_historical_signals(
        signal_state=signal_state,
        market_type=market_type,
        limit=limit,
    )
    return {
        "total": len(signals),
        "filter": {
            "signal_state": signal_state,
            "market_type": market_type,
        },
        "signals": signals,
    }


@router.post("/batch")
async def batch_evaluate_recommendations(
    req: BatchEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_optional_user),
):
    """
    Batch evaluate recommendations across multiple matches.
    """
    engine = RecommendationEngine(db=db)
    results = []
    for item in req.matches:
        rec = engine.generate_recommendation(
            match_id=item.match_id,
            home_team=item.home_team,
            away_team=item.away_team,
            market_type=item.market_type,
            category=item.category,
            home_prob=item.home_prob,
            draw_prob=item.draw_prob,
            away_prob=item.away_prob,
            market_odds=item.market_odds,
            individual_results=item.individual_results,
            feature_completeness=item.feature_completeness,
        )
        if item.match_id and item.save_to_history:
            await engine.save_signal_history(item.match_id, rec)
        results.append(rec)

    return {
        "total_evaluated": len(results),
        "recommendations": results,
    }


@router.get("/health")
async def recommendation_health():
    """
    Check health and capabilities of the Recommendation Engine.
    """
    return {
        "status": "healthy",
        "supported_market_types": ["sports", "niche"],
        "supported_states": [
            STATE_QUALIFIED_SIGNAL,
            STATE_LOW_CONFIDENCE,
            STATE_HIGH_DISAGREEMENT,
            STATE_DATA_DEFICIENT,
            STATE_NO_SIGNAL,
        ],
        "calibration_enabled": True,
        "historical_tracking_enabled": True,
    }
