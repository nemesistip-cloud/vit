"""
Results Verification & Prediction Evaluation API Endpoints — Wave 2 Prediction Intelligence.

Provides informational views for match result observations, verification status,
independent source agreement, and model-versioned prediction performance analytics.
Excludes financial wagering, sports staking, and wallet settlement features.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.modules.sports.models import ResultObservation, ResultVerification
from app.services.result_verification_service import ResultVerificationService
from app.services.prediction_evaluation_service import PredictionEvaluationService
from app.api.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/results-verification", tags=["results-verification"], dependencies=[Depends(verify_api_key)])


@router.get("/verification/{match_id}")
async def get_result_verification(
    match_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieve consolidated result verification status and history for a match."""
    stmt = select(ResultVerification).where(ResultVerification.match_id == match_id)
    res = await db.execute(stmt)
    verification = res.scalar_one_or_none()

    if not verification:
        return {
            "match_id": match_id,
            "verification_status": "PENDING_RESULT",
            "source_count": 0,
            "agreement_ratio": None,
            "verification_reason": "No verification evaluation recorded yet for this match.",
            "last_verified_at": None,
        }

    return {
        "match_id": verification.match_id,
        "verification_status": verification.verification_status,
        "primary_provider": verification.primary_provider,
        "secondary_provider": verification.secondary_provider,
        "verified_home_goals": verification.verified_home_goals,
        "verified_away_goals": verification.verified_away_goals,
        "verified_outcome": verification.verified_outcome,
        "source_count": verification.source_count,
        "agreement_ratio": verification.agreement_ratio,
        "verification_reason": verification.verification_reason,
        "is_correction": verification.is_correction,
        "correction_history": verification.correction_history or [],
        "last_verified_at": verification.last_verified_at.isoformat() if verification.last_verified_at else None,
    }


@router.get("/observations/{match_id}")
async def get_result_observations(
    match_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieve raw provider result observations and version history for a match."""
    stmt = (
        select(ResultObservation)
        .where(ResultObservation.match_id == match_id)
        .order_by(ResultObservation.provider_name, ResultObservation.version.desc())
    )
    res = await db.execute(stmt)
    observations = res.scalars().all()

    obs_list = []
    for obs in observations:
        obs_list.append({
            "id": obs.id,
            "match_id": obs.match_id,
            "provider_name": obs.provider_name,
            "provider_event_id": obs.provider_event_id,
            "competition_name": obs.competition_name,
            "home_team": obs.home_team,
            "away_team": obs.away_team,
            "home_goals": obs.home_goals,
            "away_goals": obs.away_goals,
            "reported_outcome": obs.reported_outcome,
            "status": obs.status,
            "version": obs.version,
            "validation_outcome": obs.validation_outcome,
            "content_hash": obs.content_hash,
            "local_timestamp": obs.local_timestamp.isoformat() if obs.local_timestamp else None,
            "provider_timestamp": obs.provider_timestamp.isoformat() if obs.provider_timestamp else None,
        })

    return {
        "match_id": match_id,
        "total_observations": len(obs_list),
        "observations": obs_list,
    }


@router.get("/analytics")
async def get_prediction_evaluation_analytics(
    sport: Optional[str] = Query(default=None, description="Filter by sport (e.g. football, basketball, or all)"),
    league: Optional[str] = Query(default=None, description="Filter by league/competition"),
    exclude_demo: bool = Query(default=True, description="Exclude demo/synthetic seed matches"),
    time_window_days: Optional[int] = Query(default=30, description="Time window in days for evaluation"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get trustworthy prediction performance analytics over verified match outcomes."""
    analytics = await PredictionEvaluationService.get_performance_analytics(
        db=db,
        sport=sport,
        league=league,
        exclude_demo=exclude_demo,
        time_window_days=time_window_days,
    )
    return analytics


@router.post("/ingest-and-verify/{match_id}")
async def ingest_and_verify_match_result(
    match_id: int,
    provider_name: str,
    raw_status: str,
    home_goals: Optional[int] = None,
    away_goals: Optional[int] = None,
    provider_event_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Ingest a result observation from an external provider and execute independent verification.
    Informational output only — strictly isolated from financial/wallet settlement.
    """
    # 1. Record observation
    obs = await ResultVerificationService.record_observation(
        db=db,
        match_id=match_id,
        provider_name=provider_name,
        provider_event_id=provider_event_id,
        home_goals=home_goals,
        away_goals=away_goals,
        raw_status=raw_status,
    )

    # 2. Run verification
    verification = await ResultVerificationService.verify_match_result(db=db, match_id=match_id)

    # 3. Evaluate predictions if verified
    eval_res = {}
    if verification.verification_status == "VERIFIED":
        eval_res = await PredictionEvaluationService.evaluate_match_predictions(db=db, match_id=match_id)

    await db.commit()

    return {
        "match_id": match_id,
        "observation_version": obs.version,
        "validation_outcome": obs.validation_outcome,
        "verification_status": verification.verification_status,
        "verification_reason": verification.verification_reason,
        "evaluation_summary": eval_res,
    }
