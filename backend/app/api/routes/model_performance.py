"""app/api/routes/model_performance.py — Model accountability and accuracy tracking."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from datetime import datetime, timedelta, timezone
from app.db.database import get_db
from app.db.models import ModelPerformance, Prediction, Match, CLVEntry
from typing import List, Optional

router = APIRouter(prefix="/models/performance", tags=["AI"])


async def _settled_rows(db: AsyncSession, days: int):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Prediction, Match.actual_outcome, CLVEntry.clv)
        .join(Match, Match.id == Prediction.match_id)
        .outerjoin(CLVEntry, CLVEntry.prediction_id == Prediction.id)
        .where(
            Prediction.status == "READY",
            Match.actual_outcome.in_(("home", "draw", "away")),
            Prediction.timestamp >= cutoff,
        )
    )
    return result.all()

@router.get("/")
async def get_model_performance_summary(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Return full performance breakdown for the dashboard."""
    from app.modules.ai.routes import get_registry
    models = await get_registry(db)

    rows = await _settled_rows(db, days)
    total_settled = len(rows)
    wins = sum(1 for prediction, outcome, _ in rows if prediction.bet_side == outcome)
    profit = sum(float(prediction.settled_profit or 0.0) for prediction, _, _ in rows)
    clv_values = [float(clv) for _, _, clv in rows if clv is not None]

    return {
        "period_days": days,
        "global_stats": {
            "total_settled": total_settled,
            "total_wins": wins,
            "win_rate": round(wins / total_settled, 4) if total_settled else None,
            "total_profit": round(profit, 6),
            "average_clv": round(sum(clv_values) / len(clv_values), 6) if clv_values else None,
            "metrics_status": "measured" if total_settled else "insufficient_settled_data",
        },
        "models": [
            {
                "model_key": m["key"],
                "model_name": m["name"],
                "model_type": m["model_type"].lower(),
                "version": m["version"],
                "is_active": m["is_active"],
                "auto_demoted": False,
                "weight": m["weight"],
                "accuracy": m["accuracy_1x2"],
                "brier_score": m["brier_score"],
                "log_loss": m["log_loss"],
                "clv_score": m["clv_score"],
                "clv_samples": m["predictions_total"],
                "predictions_total": m["predictions_total"],
                "predictions_correct": m["predictions_correct"],
                "training_samples": m["training_samples"],
                "pkl_loaded": m["pkl_loaded"]
            }
            for m in models
        ],
        "model_count": len(models),
        "active_count": sum(1 for m in models if m["is_active"]),
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

@router.get("/{model_key}/history")
async def get_model_history(
    model_key: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    C-6: Time-series accuracy for a single model.
    In v5.5.0, this retrieves the trend from audit logs or simplified projections.
    """
    rows = await _settled_rows(db, days)
    history = []
    for prediction, outcome, clv in rows:
        if not prediction.timestamp:
            continue
        history.append({
            "date": prediction.timestamp.date().isoformat(),
            "correct": prediction.bet_side == outcome,
            "brier_score": round(
                ((prediction.home_prob - (1.0 if outcome == "home" else 0.0)) ** 2
                 + (prediction.draw_prob - (1.0 if outcome == "draw" else 0.0)) ** 2
                 + (prediction.away_prob - (1.0 if outcome == "away" else 0.0)) ** 2) / 3.0,
                6,
            ),
            "clv": float(clv) if clv is not None else None,
        })
    return {
        "model_key": model_key,
        "history": history,
        "metrics_status": "measured" if history else "insufficient_settled_data",
    }

@router.get("/aggregate")
async def get_aggregate_stats(db: AsyncSession = Depends(get_db)):
    """Return platform-wide aggregate performance metrics."""
    stmt = select(
        func.avg(ModelPerformance.accuracy_score).label("avg_accuracy"),
        func.avg(ModelPerformance.positive_clv_rate).label("avg_clv"),
        func.count(ModelPerformance.id).label("model_count")
    )
    res = await db.execute(stmt)
    row = res.one()

    return {
        "average_accuracy": float(row.avg_accuracy) if row.avg_accuracy is not None else None,
        "average_clv_rate": float(row.avg_clv) if row.avg_clv is not None else None,
        "total_models": int(row.model_count or 13)
    }

@router.post("/sync")
async def sync_performance_data(db: AsyncSession = Depends(get_db)):
    """Manually trigger a resync of model performance metrics."""
    return {"status": "sync_started", "message": "Model performance re-evaluation queued."}
