"""app/api/routes/stats.py — Platform Statistics & Dashboard API.

GET /api/stats/dashboard    — Full platform stats (users, predictions, economy)
GET /api/stats/accuracy     — Prediction accuracy breakdown by model / league
GET /api/stats/models       — Per-model performance summary
GET /api/stats/leaderboard  — Top predictors leaderboard
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import verify_api_key
from app.db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v or default)
    except (TypeError, ValueError):
        return default


@router.get("/dashboard")
async def stats_dashboard(
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
):
    """
    Full platform statistics dashboard.

    Includes: user counts, prediction stats, model accuracy,
    economy (VITCoin), top performers, and recent activity.
    """
    from app.db.models import (
        User, Prediction, Match, CLVEntry, ModelPerformance,
        AgentInsight,
    )

    now = datetime.now(timezone.utc)
    since_30d = now - timedelta(days=30)
    since_7d  = now - timedelta(days=7)

    # ── Users ──────────────────────────────────────────────
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_30d  = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= since_30d)
    )).scalar() or 0

    # ── Predictions ───────────────────────────────────────
    total_preds = (await db.execute(select(func.count(Prediction.id)))).scalar() or 0
    preds_7d    = (await db.execute(
        select(func.count(Prediction.id)).where(Prediction.timestamp >= since_7d)
    )).scalar() or 0
    settled     = (await db.execute(
        select(func.count(Prediction.id)).where(Prediction.was_correct.isnot(None))
    )).scalar() or 0
    correct     = (await db.execute(
        select(func.count(Prediction.id)).where(Prediction.was_correct == True)
    )).scalar() or 0

    accuracy = round((correct / settled * 100) if settled > 0 else 0.0, 1)

    # ── Average edge ─────────────────────────────────────
    avg_edge = (await db.execute(
        select(func.avg(Prediction.vig_free_edge)).where(
            Prediction.vig_free_edge.isnot(None)
        )
    )).scalar()
    avg_edge = _safe_float(avg_edge)

    avg_confidence = (await db.execute(
        select(func.avg(Prediction.confidence)).where(
            Prediction.confidence.isnot(None)
        )
    )).scalar()
    avg_confidence = _safe_float(avg_confidence)

    # ── CLV / Profit ──────────────────────────────────────
    total_profit = (await db.execute(
        select(func.coalesce(func.sum(CLVEntry.profit), 0))
    )).scalar()
    total_profit = _safe_float(total_profit)

    # ── Models ────────────────────────────────────────────
    from app.core.dependencies import get_orchestrator
    orch = get_orchestrator()
    model_status = orch.get_model_status() if orch else {"models": [], "total": 0, "ready": 0}
    models_total = model_status.get("total", 0)
    models_ready = model_status.get("ready", 0)

    # ── Agents ────────────────────────────────────────────
    try:
        from app.core.swarm_orchestrator import get_swarm
        swarm = get_swarm()
        health = swarm.health_summary() if swarm else {}
        agents_running = health.get("running", 0)
        agents_total   = health.get("total", 22)
    except Exception:
        agents_running, agents_total = 0, 22

    # ── Recent agent insights ────────────────────────────
    recent_insights = []
    try:
        q = (
            select(AgentInsight)
            .order_by(desc(AgentInsight.created_at))
            .limit(5)
        )
        rows = list((await db.execute(q)).scalars().all())
        recent_insights = [
            {
                "agent_name":   r.agent_name,
                "insight_type": r.insight_type,
                "content":      (r.content or "")[:200],
                "created_at":   r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    except Exception:
        pass

    # ── Economy (VITCoin) ────────────────────────────────
    vitcoin_supply = 0.0
    total_staked   = 0.0
    try:
        from app.modules.wallet.models import WalletTransaction
        total_staked_res = await db.execute(
            select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where(
                WalletTransaction.type == "stake",
                WalletTransaction.status.in_(["confirmed", "completed"]),
            )
        )
        total_staked = _safe_float(total_staked_res.scalar())
    except Exception:
        pass

    try:
        from app.modules.wallet.models import Wallet
        supply_res = await db.execute(
            select(func.coalesce(func.sum(Wallet.balance), 0))
        )
        vitcoin_supply = _safe_float(supply_res.scalar())
    except Exception:
        pass

    return {
        "generated_at": now.isoformat(),
        "users": {
            "total":     total_users,
            "new_30d":   active_30d,
        },
        "predictions": {
            "total":          total_preds,
            "last_7d":        preds_7d,
            "settled":        settled,
            "correct":        correct,
            "accuracy_pct":   accuracy,
            "avg_edge":       round(avg_edge, 4),
            "avg_confidence": round(avg_confidence, 4),
            "total_profit":   round(total_profit, 2),
        },
        "models": {
            "total":          models_total,
            "ready":          models_ready,
            "models_list":    model_status.get("models", [])[:13],
        },
        "agents": {
            "running": agents_running,
            "total":   agents_total,
        },
        "economy": {
            "vitcoin_supply": round(vitcoin_supply, 2),
            "total_staked":   round(total_staked, 2),
        },
        "recent_insights": recent_insights,
    }


@router.get("/accuracy")
async def stats_accuracy(
    league: Optional[str] = Query(None),
    days:   int           = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
):
    """Prediction accuracy breakdown optionally filtered by league and time range."""
    from app.db.models import Prediction, Match

    since = datetime.now(timezone.utc) - timedelta(days=days)

    from sqlalchemy import case
    stmt = (
        select(
            Match.league,
            func.count(Prediction.id),
            func.sum(case((Prediction.was_correct == True, 1), else_=0)),
        )
        .join(Match, Match.id == Prediction.match_id)
        .where(
            Prediction.was_correct.isnot(None),
            Prediction.timestamp >= since,
        )
    )
    if league:
        stmt = stmt.where(Match.league == league)
    stmt = stmt.group_by(Match.league).order_by(desc(func.count(Prediction.id)))

    rows = list((await db.execute(stmt)).all())

    breakdown = []
    for lg, total, wins in rows:
        breakdown.append({
            "league":       lg or "unknown",
            "total":        int(total or 0),
            "correct":      int(wins or 0),
            "accuracy_pct": round((int(wins or 0) / int(total)) * 100, 1) if total else 0.0,
        })

    overall_total   = sum(r["total"]   for r in breakdown)
    overall_correct = sum(r["correct"] for r in breakdown)

    return {
        "period_days":    days,
        "overall": {
            "total":        overall_total,
            "correct":      overall_correct,
            "accuracy_pct": round((overall_correct / overall_total * 100) if overall_total else 0.0, 1),
        },
        "by_league": breakdown,
    }


@router.get("/models")
async def stats_models(
    _user=Depends(verify_api_key),
):
    """Per-model performance summary from the Brier-weighted ensemble."""
    try:
        from app.ml.ensemble.weighted import get_brier_ensemble
        ensemble = get_brier_ensemble()
        weights = ensemble.get_weights()
        brier   = ensemble._brier_scores
        samples = ensemble._sample_counts

        models = []
        for name, w in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            models.append({
                "model_name":      name,
                "weight":          round(w, 5),
                "brier_score":     round(brier.get(name, 0.0), 5),
                "sample_count":    samples.get(name, 0),
            })

        return {
            "count":       len(models),
            "models":      models,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("[stats] models error: %s", exc)
        return {"count": 0, "models": [], "error": str(exc)}
