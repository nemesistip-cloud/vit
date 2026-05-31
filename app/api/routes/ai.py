"""AI Management API endpoints"""

import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import AIPrediction
from app.services.ai_ingestion import AIIngestionService
from app.services.ai_profiler import AIProfilerService
from app.services.ai_signals import AISignalService
from app.api.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai",
    tags=["ai"],
    dependencies=[Depends(verify_api_key)]
)


@router.get("/predictions")
async def list_ai_predictions(
    match_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List AI predictions, optionally filtered by match."""
    query = select(AIPrediction)
    if match_id is not None:
        query = query.where(AIPrediction.match_id == match_id)

    result = await db.execute(query.offset(offset).limit(limit))
    predictions = result.scalars().all()
    return {
        "predictions": [
            {
                "match_id": p.match_id,
                "source": p.source,
                "home_prob": p.home_prob,
                "draw_prob": p.draw_prob,
                "away_prob": p.away_prob,
                "confidence": p.confidence,
                "reason": p.reason,
                "timestamp": p.timestamp,
            }
            for p in predictions
        ]
    }


@router.get("/predictions/{match_id}")
async def get_ai_predictions(
    match_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all AI predictions for a match"""
    service = AIIngestionService(db)
    predictions = await service.get_predictions_for_match(match_id)
    return {"match_id": match_id, "predictions": predictions}


@router.post("/predictions")
async def ingest_ai_prediction(
    match_id: int,
    source: str,
    home_prob: float,
    draw_prob: float,
    away_prob: float,
    confidence: float = 0.7,
    reason: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Manually ingest an AI prediction"""
    service = AIIngestionService(db)

    success = await service.ingest_prediction(
        match_id=match_id,
        source=source,
        home_prob=home_prob,
        draw_prob=draw_prob,
        away_prob=away_prob,
        confidence=confidence,
        reason=reason
    )

    if success:
        return {"status": "success", "message": f"AI prediction ingested for match {match_id}"}
    else:
        raise HTTPException(status_code=400, detail="Failed to ingest AI prediction")


@router.get("/performance")
async def get_ai_performance(
    source: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get AI performance metrics"""
    service = AIIngestionService(db)
    performance = await service.get_ai_performance(source)
    return performance


@router.post("/performance/update")
async def update_ai_performance(db: AsyncSession = Depends(get_db)):
    """Update AI performance metrics after matches complete"""
    service = AIIngestionService(db)
    await service.update_performance_metrics()
    return {"status": "success", "message": "AI performance metrics updated"}


@router.get("/signals/{match_id}")
async def get_ai_signals(
    match_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get AI signals for a match"""
    service = AISignalService(db)
    signals = await service.get_signals_for_match(match_id)
    return {"match_id": match_id, "signals": signals}


@router.post("/weights/update")
async def update_ai_weights(db: AsyncSession = Depends(get_db)):
    """Update dynamic weights for AI sources"""
    service = AIProfilerService(db)
    await service.update_weights()
    return {"status": "success", "message": "AI weights updated"}


@router.get("/report")
async def get_performance_report(db: AsyncSession = Depends(get_db)):
    """Get comprehensive AI performance report"""
    service = AIProfilerService(db)
    report = await service.get_performance_report()
    return report


@router.get("/multi-insights/{match_id}")
async def get_multi_ai_insights(
    match_id: int,
    sources: str = "gemini,claude,grok",
    db: AsyncSession = Depends(get_db),
):
    """
    Fan-out to selected AI providers in parallel, return per-provider
    tactical insights + probability assessments and ingest into DB.
    sources: comma-separated list of: gemini, claude, grok
    """
    from app.services.multi_ai_dispatcher import run_multi_ai
    source_list = [s.strip() for s in sources.split(",") if s.strip()]
    try:
        return await run_multi_ai(match_id=match_id, db=db, sources=source_list)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Multi-AI dispatch failed for match {match_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def ai_health_check(db: AsyncSession = Depends(get_db)):
    """AI system health check"""
    try:
        # Check database connectivity
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))

        # Check AI services
        ingestion = AIIngestionService(db)
        profiler = AIProfilerService(db)
        signals = AISignalService(db)

        # Get basic stats
        performance = await ingestion.get_ai_performance()
        report = await profiler.get_performance_report()

        return {
            "status": "healthy",
            "ai_sources_tracked": len(performance),
            "total_predictions": sum(p.get("sample_size", 0) for p in performance.values()),
            "avg_accuracy": sum(p.get("accuracy", 0) for p in performance.values()) / len(performance) if performance else 0,
            "generated_at": report.get("generated_at")
        }
    except Exception as e:
        logger.error(f"AI health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }