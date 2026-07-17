# app/modules/analytics_studio/routes.py
"""
Analytics Studio — Phase VIII
Personal prediction analytics, model comparison, P&L breakdowns,
ROI curves, and leaderboard insights.
"""

from __future__ import annotations

import logging
import math
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics-studio", tags=["Analytics Studio"])


# ── Helpers (stub computations — wire to real match/prediction DB later) ──────

def _roi_curve(n_days: int = 30) -> List[dict]:
    """Synthetic 30-day rolling ROI."""
    base, roi = 0.0, 0.0
    curve = []
    for i in range(n_days):
        delta = (math.sin(i * 0.4) * 3.2 + (i / n_days) * 8)
        roi += delta
        curve.append({"day": f"D-{n_days - i}", "roi_pct": round(roi, 2)})
    return curve


def _model_comparison_mock() -> List[dict]:
    models = [
        ("XGBoost Ensemble",    0.614, 0.71, 41.2),
        ("LightGBM v3",         0.598, 0.69, 38.7),
        ("Neural Oracle",       0.622, 0.74, 44.1),
        ("Poisson Regressor",   0.581, 0.67, 35.2),
        ("Transformer v2",      0.637, 0.76, 47.8),
        ("Random Forest",       0.573, 0.65, 33.4),
        ("Bayesian Network",    0.591, 0.68, 37.1),
        ("Gradient Boosting",   0.609, 0.70, 40.5),
        ("Logistic Ensemble",   0.556, 0.63, 29.8),
        ("Deep Residual Net",   0.628, 0.73, 45.2),
        ("SVM Calibrated",      0.544, 0.61, 27.3),
        ("LSTM Sequence",       0.618, 0.72, 42.6),
        ("Catboost Ranker",     0.601, 0.70, 39.3),
    ]
    return [
        {
            "model":        name,
            "accuracy":     acc,
            "roc_auc":      roc,
            "roi_pct":      roi,
            "predictions":  int(1200 + roi * 10),
            "correct":      int((1200 + roi * 10) * acc),
        }
        for name, acc, roc, roi in models
    ]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/overview", summary="Personal analytics overview")
async def get_overview(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """High-level KPIs for the authenticated user's prediction history."""
    # Stub — in production pull from match_predictions joined with results
    return {
        "user_id":             me.id,
        "total_predictions":   142,
        "correct":             91,
        "accuracy_pct":        64.1,
        "roi_pct":             38.4,
        "total_staked_vit":    2840.0,
        "total_returned_vit":  3931.76,
        "net_pnl_vit":         1091.76,
        "best_market":         "Home Win",
        "best_market_acc":     71.2,
        "worst_market":        "Correct Score",
        "worst_market_acc":    18.5,
        "current_streak":      4,
        "best_streak":         11,
        "markets_traded":      ["Match Result", "BTTS", "Over/Under", "Correct Score"],
        "last_updated":        time.time(),
    }


@router.get("/roi-curve", summary="Rolling ROI curve (30-day default)")
async def roi_curve(
    days:  int = Query(30, ge=7,  le=365),
    me: User = Depends(get_current_user),
):
    return {"user_id": me.id, "days": days, "curve": _roi_curve(days)}


@router.get("/pnl-breakdown", summary="P&L breakdown by market type")
async def pnl_breakdown(me: User = Depends(get_current_user)):
    markets = [
        {"market": "Match Result",  "bets": 58, "correct": 38, "roi_pct": 31.2, "pnl_vit":  445.0},
        {"market": "BTTS",          "bets": 31, "correct": 21, "roi_pct": 42.7, "pnl_vit":  312.5},
        {"market": "Over/Under",    "bets": 27, "correct": 18, "roi_pct": 39.1, "pnl_vit":  278.4},
        {"market": "Correct Score", "bets": 14, "correct":  4, "roi_pct": 12.0, "pnl_vit":   55.86},
        {"market": "Asian Handicap","bets": 12, "correct":  9, "roi_pct": 55.3, "pnl_vit":  195.0},
    ]
    return {"user_id": me.id, "markets": markets}


@router.get("/accuracy-heatmap", summary="Accuracy by league and day of week")
async def accuracy_heatmap(me: User = Depends(get_current_user)):
    leagues = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
    days    = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    import random, hashlib
    rng = random.Random(me.id)
    heatmap = [
        {
            "league": lg,
            "accuracy_by_day": {
                d: round(rng.uniform(45, 80), 1) for d in days
            }
        }
        for lg in leagues
    ]
    return {"user_id": me.id, "heatmap": heatmap}


@router.get("/model-comparison", summary="Compare all 13 AI models head-to-head")
async def model_comparison(
    sort_by: str = Query("roi_pct", description="accuracy | roi_pct | roc_auc"),
):
    models = _model_comparison_mock()
    if sort_by in {"accuracy", "roi_pct", "roc_auc"}:
        models.sort(key=lambda m: m.get(sort_by, 0), reverse=True)
    return {"models": models, "ranked_by": sort_by}


@router.get("/model-comparison/{model_name}", summary="Single model deep-dive")
async def model_detail(model_name: str):
    all_models = {m["model"]: m for m in _model_comparison_mock()}
    m = all_models.get(model_name)
    if not m:
        raise HTTPException(404, f"Model '{model_name}' not found")
    # Synthetic per-league breakdown
    leagues = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
    league_perf = [
        {
            "league":   lg,
            "accuracy": round(m["accuracy"] + (hash(lg + model_name) % 20 - 10) / 100, 3),
            "bets":     int(m["predictions"] / len(leagues)),
        }
        for lg in leagues
    ]
    return {**m, "league_performance": league_perf}


@router.get("/leaderboard-insights", summary="Leaderboard trend analytics")
async def leaderboard_insights(
    me: User = Depends(get_current_user),
    top_n: int = Query(10, ge=5, le=50),
):
    """Stats on the top-N users for benchmarking."""
    import random as rnd
    rnd.seed(42)
    top = [
        {
            "rank":       i + 1,
            "user_id":    1000 + i,
            "accuracy":   round(rnd.uniform(60, 82), 1),
            "roi_pct":    round(rnd.uniform(20, 65), 1),
            "bets":       rnd.randint(80, 500),
            "streak":     rnd.randint(0, 18),
        }
        for i in range(top_n)
    ]
    return {
        "top_predictors":   top,
        "my_rank":          42,   # stub
        "percentile":       71.3, # stub
    }


@router.get("/calibration", summary="Prediction calibration (reliability diagram)")
async def calibration_data(me: User = Depends(get_current_user)):
    """Reliability diagram: predicted probability vs observed frequency."""
    buckets = [round(i * 0.1, 1) for i in range(1, 10)]
    import random as rnd
    rnd.seed(me.id)
    data = [
        {
            "predicted_prob":  b,
            "observed_freq":   round(b + rnd.uniform(-0.08, 0.08), 3),
            "sample_size":     rnd.randint(15, 120),
        }
        for b in buckets
    ]
    return {"user_id": me.id, "calibration": data}
