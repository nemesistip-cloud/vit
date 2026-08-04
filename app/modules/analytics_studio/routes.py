# app/modules/analytics_studio/routes.py
"""
Analytics Studio — Phase VIII (Real DB)
Personal prediction analytics, model comparison, P&L breakdowns,
ROI curves, and leaderboard insights — all wired to live data.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User, Prediction, Match

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics-studio", tags=["Analytics Studio"])

# ── helpers ──────────────────────────────────────────────────────────────────

def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return round(a / b, 4) if b else default


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/overview", summary="Personal analytics overview")
async def get_overview(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """High-level KPIs from the authenticated user's real prediction history."""
    preds_q = await db.execute(
        select(Prediction).where(Prediction.user_id == me.id)
    )
    preds: List[Prediction] = list(preds_q.scalars().all())

    total = len(preds)
    settled = [p for p in preds if p.settled_profit is not None]
    correct = [p for p in settled if p.was_correct is True]
    staked = sum(float(p.submitted_stake or 0) for p in settled)
    returned = staked + sum(float(p.settled_profit or 0) for p in settled)
    net_pnl = returned - staked

    accuracy_pct = _safe_div(len(correct) * 100, len(settled))
    roi_pct = _safe_div(net_pnl * 100, staked)

    # Best/worst market
    market_stats: dict[str, dict] = {}
    for p in settled:
        mkt = p.submitted_market_side or p.bet_side or "Unknown"
        ms = market_stats.setdefault(mkt, {"correct": 0, "total": 0})
        ms["total"] += 1
        if (p.settled_profit or 0) > 0:
            ms["correct"] += 1

    best_mkt, best_acc = "N/A", 0.0
    worst_mkt, worst_acc = "N/A", 100.0
    for mkt, ms in market_stats.items():
        acc = _safe_div(ms["correct"] * 100, ms["total"])
        if acc > best_acc:
            best_mkt, best_acc = mkt, acc
        if acc < worst_acc:
            worst_mkt, worst_acc = mkt, acc

    # Streak
    streak = 0
    best_streak = 0
    cur = 0
    for p in sorted(settled, key=lambda x: x.timestamp or datetime.min):
        if (p.settled_profit or 0) > 0:
            cur += 1
            best_streak = max(best_streak, cur)
        else:
            cur = 0
    streak = cur

    return {
        "user_id":             me.id,
        "total_predictions":   total,
        "settled_predictions": len(settled),
        "correct":             len(correct),
        "accuracy_pct":        round(accuracy_pct, 2),
        "roi_pct":             round(roi_pct, 2),
        "total_staked_vit":    round(staked, 4),
        "total_returned_vit":  round(returned, 4),
        "net_pnl_vit":         round(net_pnl, 4),
        "best_market":         best_mkt,
        "best_market_acc":     round(best_acc, 2),
        "worst_market":        worst_mkt,
        "worst_market_acc":    round(worst_acc, 2) if worst_acc < 100.0 else 0.0,
        "current_streak":      streak,
        "best_streak":         best_streak,
        "markets_traded":      list(market_stats.keys()),
        "last_updated":        time.time(),
    }


@router.get("/roi-curve", summary="Rolling ROI curve")
async def roi_curve(
    days: int = Query(30, ge=7, le=365),
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    preds_q = await db.execute(
        select(Prediction).where(
            Prediction.user_id == me.id,
            Prediction.settled_profit.isnot(None),
            Prediction.timestamp >= since,
        ).order_by(Prediction.timestamp)
    )
    preds = list(preds_q.scalars().all())

    # Aggregate by day
    day_map: dict[str, float] = {}
    for p in preds:
        key = (p.timestamp or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
        day_map[key] = day_map.get(key, 0.0) + float(p.settled_profit or 0)

    cumulative = 0.0
    curve = []
    for day_key in sorted(day_map):
        cumulative += day_map[day_key]
        curve.append({"day": day_key, "roi_pct": round(cumulative, 4)})

    return {"user_id": me.id, "days": days, "curve": curve}


@router.get("/pnl-breakdown", summary="P&L breakdown by market type")
async def pnl_breakdown(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    preds_q = await db.execute(
        select(Prediction).where(
            Prediction.user_id == me.id,
            Prediction.settled_profit.isnot(None),
        )
    )
    preds = list(preds_q.scalars().all())

    market_map: dict[str, dict] = {}
    for p in settled_p := preds:
        mkt = p.submitted_market_side or p.bet_side or "Unknown"
        m = market_map.setdefault(mkt, {"bets": 0, "correct": 0, "pnl_vit": 0.0})
        m["bets"] += 1
        profit = float(p.settled_profit or 0)
        m["pnl_vit"] += profit
        if p.was_correct is True:
            m["correct"] += 1

    total_staked = sum(float(p.submitted_stake or 0) for p in settled_p)
    markets = []
    for mkt, m in market_map.items():
        roi_pct = _safe_div(m["pnl_vit"] * 100, total_staked) if total_staked else 0.0
        markets.append({
            "market":   mkt,
            "bets":     m["bets"],
            "correct":  m["correct"],
            "roi_pct":  round(roi_pct, 2),
            "pnl_vit":  round(m["pnl_vit"], 4),
        })
    markets.sort(key=lambda x: x["pnl_vit"], reverse=True)

    return {"user_id": me.id, "markets": markets}


@router.get("/accuracy-heatmap", summary="Accuracy by league and day of week")
async def accuracy_heatmap(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    preds_q = await db.execute(
        select(Prediction, Match).join(Match, Prediction.match_id == Match.id, isouter=True).where(
            Prediction.user_id == me.id,
            Prediction.settled_profit.isnot(None),
        )
    )
    rows = preds_q.all()

    # league → day → {correct, total}
    heatmap_data: dict[str, dict[str, dict]] = {}
    for pred, match in rows:
        league = (match.league if match else None) or "Unknown"
        created = pred.timestamp or datetime.now(timezone.utc)
        day = created.strftime("%a")
        l_map = heatmap_data.setdefault(league, {})
        d_map = l_map.setdefault(day, {"correct": 0, "total": 0})
        d_map["total"] += 1
        if pred.was_correct is True:
            d_map["correct"] += 1

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    heatmap = [
        {
            "league": lg,
            "accuracy_by_day": {
                d: round(_safe_div(heatmap_data[lg].get(d, {}).get("correct", 0) * 100,
                                   heatmap_data[lg].get(d, {}).get("total", 0)), 1)
                for d in days
            },
        }
        for lg in heatmap_data
    ]
    return {"user_id": me.id, "heatmap": heatmap}


@router.get("/model-comparison", summary="Compare AI models from live registry")
async def model_comparison(
    sort_by: str = Query("roi_pct", description="accuracy | roi_pct | roc_auc"),
    db: AsyncSession = Depends(get_db),
):
    """Returns real model performance from the AI model registry."""
    from app.modules.ai.models import ModelMetadata
    rows_q = await db.execute(select(ModelMetadata).where(ModelMetadata.is_active == True))
    rows = list(rows_q.scalars().all())

    models = []
    for r in rows:
        m_metrics = r.metrics or {}
        models.append({
            "model":       r.name,
            "key":         r.key,
            "accuracy":    round(float(m_metrics.get("accuracy", 0)), 3),
            "roc_auc":     round(float(m_metrics.get("roc_auc", 0)), 3),
            "roi_pct":     round(float(m_metrics.get("roi_pct", 0)), 2),
            "predictions": int(m_metrics.get("predictions", 0)),
            "correct":     int(m_metrics.get("correct", 0)),
            "weight":      float(r.weight or 1.0),
            "version":     r.version,
            "is_active":   r.is_active,
        })

    valid_sorts = {"accuracy", "roi_pct", "roc_auc", "weight"}
    if sort_by in valid_sorts:
        models.sort(key=lambda m: m.get(sort_by, 0), reverse=True)

    return {"models": models, "ranked_by": sort_by, "total": len(models)}


@router.get("/model-comparison/{model_key}", summary="Single model deep-dive")
async def model_detail(
    model_key: str,
    db: AsyncSession = Depends(get_db),
):
    from app.modules.ai.models import ModelMetadata
    from fastapi import HTTPException
    row_q = await db.execute(select(ModelMetadata).where(ModelMetadata.key == model_key))
    row = row_q.scalar_one_or_none()
    if not row:
        raise HTTPException(404, f"Model '{model_key}' not found in registry")

    m_metrics = row.metrics or {}
    return {
        "key":              row.key,
        "model":            row.name,
        "accuracy":         round(float(m_metrics.get("accuracy", 0)), 3),
        "roc_auc":          round(float(m_metrics.get("roc_auc", 0)), 3),
        "roi_pct":          round(float(m_metrics.get("roi_pct", 0)), 2),
        "predictions":      int(m_metrics.get("predictions", 0)),
        "correct":          int(m_metrics.get("correct", 0)),
        "weight":           float(row.weight or 1.0),
        "version":          row.version,
        "version_history":  row.version_history or [],
        "supported_markets": row.supported_markets or [],
        "description":      row.description,
        "is_active":        row.is_active,
        "last_trained_at":  row.last_trained_at.isoformat() if row.last_trained_at else None,
    }


@router.get("/leaderboard-insights", summary="Leaderboard analytics from real data")
async def leaderboard_insights(
    me: User = Depends(get_current_user),
    top_n: int = Query(10, ge=5, le=50),
    db: AsyncSession = Depends(get_db),
):
    # Aggregate per-user from settled predictions
    rows_q = await db.execute(
        select(
            Prediction.user_id,
            func.count(Prediction.id).label("bets"),
            func.sum(case((Prediction.was_correct == True, 1), else_=0)).label("correct"),
            func.sum(Prediction.settled_profit).label("total_profit"),
            func.max(Prediction.settled_profit).label("best_profit"),
        ).where(
            Prediction.settled_profit.isnot(None)
        ).group_by(Prediction.user_id).order_by(desc("total_profit")).limit(top_n)
    )
    rows = rows_q.all()

    top = []
    my_rank = None
    for idx, row in enumerate(rows):
        bets = int(row.bets or 0)
        correct = int(row.correct or 0)
        acc = _safe_div(correct * 100, bets)
        top.append({
            "rank":       idx + 1,
            "user_id":    row.user_id,
            "accuracy":   round(acc, 1),
            "roi_pct":    round(float(row.total_profit or 0), 2),
            "bets":       bets,
            "correct":    correct,
        })
        if row.user_id == me.id:
            my_rank = idx + 1

    # Estimate my rank if not in top_n
    if my_rank is None:
        rank_q = await db.execute(
            select(func.count()).select_from(
                select(
                    Prediction.user_id,
                    func.sum(Prediction.settled_profit).label("tp"),
                ).where(Prediction.settled_profit.isnot(None)).group_by(Prediction.user_id).subquery()
            ).where(text("tp > (SELECT COALESCE(SUM(settled_profit),0) FROM predictions WHERE user_id = :uid AND settled_profit IS NOT NULL)")).params(uid=me.id)
        )
        my_rank = (rank_q.scalar() or 0) + 1

    total_users_q = await db.execute(
        select(func.count(func.distinct(Prediction.user_id))).where(Prediction.settled_profit.isnot(None))
    )
    total_users = total_users_q.scalar() or 1
    percentile = round(_safe_div((total_users - my_rank) * 100, total_users), 1)

    return {
        "top_predictors": top,
        "my_rank":        my_rank,
        "percentile":     percentile,
        "total_users":    total_users,
    }


@router.get("/calibration", summary="Prediction calibration reliability diagram")
async def calibration_data(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    preds_q = await db.execute(
        select(Prediction).where(
            Prediction.user_id == me.id,
            Prediction.settled_profit.isnot(None),
            Prediction.consensus_prob.isnot(None),
        )
    )
    preds = list(preds_q.scalars().all())

    # Build 10 buckets [0.1, 0.2, ..., 1.0]
    buckets: dict[float, dict] = {round(i * 0.1, 1): {"total": 0, "correct": 0} for i in range(1, 11)}
    for p in preds:
        prob = float(p.consensus_prob or 0)
        bucket = round(min(round(prob * 10) / 10, 1.0), 1)
        if bucket in buckets:
            buckets[bucket]["total"] += 1
            if p.was_correct is True:
                buckets[bucket]["correct"] += 1

    data = []
    for b, vals in sorted(buckets.items()):
        obs = _safe_div(vals["correct"], vals["total"]) if vals["total"] else None
        data.append({
            "predicted_prob":  b,
            "observed_freq":   round(obs, 3) if obs is not None else None,
            "sample_size":     vals["total"],
        })

    return {"user_id": me.id, "calibration": data, "total_settled": len(preds)}
