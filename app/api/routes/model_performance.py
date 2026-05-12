"""app/api/routes/model_performance.py
Model Performance Dashboard — Phase 3b
GET /api/models/performance  → per-model accuracy, Sharpe, ROI, trend
GET /api/models/performance/summary → aggregate stats
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Prediction, Match, ModelPerformance
from app.modules.ai.models import ModelMetadata
from app.services.cache import cache

# Ensure all relationship-referenced models are registered before mapper configures
import app.modules.notifications.models  # registers Notification, NotificationPreference  # noqa: F401

router = APIRouter(prefix="/api/models", tags=["Model Performance"])
logger = logging.getLogger(__name__)


def _sharpe(profits: List[float]) -> float:
    if len(profits) < 2:
        return 0.0
    import statistics
    mean = statistics.mean(profits)
    stdev = statistics.stdev(profits)
    if stdev == 0:
        return 0.0
    return round(mean / stdev, 4)


def _trend(values: List[float], window: int = 5) -> str:
    if len(values) < window:
        return "neutral"
    recent = values[-window:]
    if recent[-1] > recent[0] * 1.02:
        return "improving"
    if recent[-1] < recent[0] * 0.98:
        return "declining"
    return "stable"


@router.get("/performance")
async def get_model_performance(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns per-model performance stats from the ModelMetadata registry
    combined with computed metrics from settled predictions.
    """
    cache_key = f"model_performance:{days}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Load all active models from the registry
    meta_res = await db.execute(select(ModelMetadata).order_by(ModelMetadata.key))
    models = meta_res.scalars().all()

    # Aggregate settled prediction stats (global, not per-model since predictions
    # are ensemble-level, not per-model-level)
    settled_res = await db.execute(
        select(
            func.count(Prediction.id).label("total"),
            func.sum(
                case((Prediction.was_correct == True, 1.0), else_=0.0)  # noqa: E712
            ).label("wins"),
            func.coalesce(func.sum(Prediction.settled_profit), 0.0).label("profit"),
        ).join(Match, Match.id == Prediction.match_id).where(
            and_(
                Match.actual_outcome.isnot(None),
                Prediction.was_correct.isnot(None),
                Prediction.timestamp >= cutoff,
            )
        )
    )
    agg = settled_res.one()
    total_settled = int(agg.total or 0)
    total_wins = int(agg.wins or 0)
    total_profit = float(agg.profit or 0.0)
    global_win_rate = round(total_wins / total_settled * 100, 1) if total_settled else 0.0

    # Recent prediction profits (last 90 for Sharpe)
    recent_profits_res = await db.execute(
        select(Prediction.settled_profit).join(Match, Match.id == Prediction.match_id).where(
            and_(
                Match.actual_outcome.isnot(None),
                Prediction.settled_profit.isnot(None),
                Prediction.timestamp >= cutoff,
            )
        ).order_by(Prediction.timestamp)
    )
    profit_series = [float(r[0]) for r in recent_profits_res.all()]
    global_sharpe = _sharpe(profit_series)

    # Build per-model rows from ModelMetadata
    rows: List[Dict[str, Any]] = []
    for m in models:
        acc = m.accuracy_1x2 or m.accuracy
        rows.append({
            "model_key":       m.key,
            "model_name":      m.name,
            "model_type":      m.model_type,
            "version":         m.version,
            "is_active":       m.is_active,
            "auto_demoted":    bool(m.auto_demoted),
            "weight":          round(float(m.weight or 1.0), 4),
            "accuracy":        round(float(acc or 0.0), 4) if acc is not None else None,
            "brier_score":     round(float(m.brier_score or 0.0), 4) if m.brier_score else None,
            "log_loss":        round(float(m.log_loss or 0.0), 4) if m.log_loss else None,
            "clv_score":       round(float(m.clv_score or 0.0), 4) if m.clv_score else None,
            "clv_samples":     m.clv_samples or 0,
            "predictions_total":   m.predictions_total or 0,
            "predictions_correct": m.predictions_correct or 0,
            "training_samples":    m.training_samples or 0,
            "pkl_loaded":          m.pkl_loaded,
        })

    result = {
        "period_days":    days,
        "global_stats": {
            "total_settled": total_settled,
            "total_wins":    total_wins,
            "win_rate":      global_win_rate,
            "total_profit":  round(total_profit, 4),
            "sharpe_ratio":  global_sharpe,
            "profit_trend":  _trend(profit_series),
        },
        "models": rows,
        "model_count": len(rows),
        "active_count": sum(1 for r in rows if r["is_active"]),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    await cache.set(cache_key, result, ttl=120)
    return result


@router.get("/performance/summary")
async def get_performance_summary(db: AsyncSession = Depends(get_db)):
    """Quick summary card — total models, accuracy, best/worst model."""
    cache_key = "model_performance_summary"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    meta_res = await db.execute(select(ModelMetadata))
    models = meta_res.scalars().all()

    active = [m for m in models if m.is_active]
    accs = [float(m.accuracy_1x2 or m.accuracy or 0) for m in active if (m.accuracy_1x2 or m.accuracy)]
    avg_acc = round(sum(accs) / len(accs), 4) if accs else 0.0

    best = max(active, key=lambda m: float(m.accuracy_1x2 or m.accuracy or 0), default=None)
    worst = min(active, key=lambda m: float(m.accuracy_1x2 or m.accuracy or 0), default=None)

    result = {
        "total_models":  len(models),
        "active_models": len(active),
        "avg_accuracy":  avg_acc,
        "best_model":    {"key": best.key, "name": best.name, "accuracy": float(best.accuracy_1x2 or best.accuracy or 0)} if best else None,
        "worst_model":   {"key": worst.key, "name": worst.name, "accuracy": float(worst.accuracy_1x2 or worst.accuracy or 0)} if worst else None,
    }

    await cache.set(cache_key, result, ttl=300)
    return result


@router.post("/performance/sync")
async def trigger_performance_sync(db: AsyncSession = Depends(get_db)):
    """Admin trigger: force the performance monitor agent to run now."""
    try:
        from app.core.swarm_orchestrator import get_swarm
        swarm = get_swarm()
        if swarm:
            agent = swarm.agents.get("performance-monitor")
            if agent:
                import asyncio
                asyncio.create_task(agent.run_cycle())
                return {"status": "triggered", "agent": "performance-monitor"}
        return {"status": "agent_not_found"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
