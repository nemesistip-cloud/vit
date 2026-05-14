"""
app/api/routes/model_breakdown.py

P3#12  GET  /api/ai-engine/predictions/{match_id}/breakdown
P3#13  GET  /api/ai-engine/backtest/walk-forward
P3#14  GET  /api/ai-engine/predictions/{match_id}/attribution
P1#6   POST /api/ai-engine/predict/live-score

All endpoints require a valid API key.
"""

import logging
import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, func, cast, String

from app.db.database import get_db
from app.api.middleware.auth import verify_api_key
from app.core.dependencies import get_orchestrator_dep

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ai-engine",
    tags=["ai-engine-extended"],
    dependencies=[Depends(verify_api_key)],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class LiveScoreRequest(BaseModel):
    match_id:    Optional[int] = Field(None, description="Optional DB match ID for feature lookup")
    home_team:   str = Field(..., min_length=2)
    away_team:   str = Field(..., min_length=2)
    league:      str = Field("unknown")
    home_score:  int = Field(..., ge=0, le=20)
    away_score:  int = Field(..., ge=0, le=20)
    minute:      int = Field(..., ge=1, le=120)
    market_odds: Optional[Dict[str, float]] = Field(
        None, description='e.g. {"home": 2.10, "draw": 3.40, "away": 3.60}'
    )


# ── P3#12: Per-model breakdown ────────────────────────────────────────────────

@router.get("/predictions/{match_id}/breakdown")
async def get_model_breakdown(
    match_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    P3#12 — Return the per-model prediction breakdown for a specific match.

    Reads `AIPredictionAudit.individual_results` for the most recent audit
    row matching the given match_id.  Returns each model's predicted probs,
    weight, calibration status, and deviation from the ensemble output.
    """
    try:
        from app.modules.ai.models import AIPredictionAudit
        result = await db.execute(
            select(AIPredictionAudit)
            .where(AIPredictionAudit.match_id == str(match_id))
            .order_by(desc(AIPredictionAudit.created_at))
            .limit(1)
        )
        audit = result.scalar_one_or_none()
        if audit is None:
            raise HTTPException(status_code=404, detail=f"No prediction audit found for match_id={match_id}")

        individual = audit.individual_results or []
        ensemble_hp = float(audit.home_prob or 0.33)
        ensemble_dp = float(audit.draw_prob or 0.33)
        ensemble_ap = float(audit.away_prob or 0.33)

        breakdown = []
        for m in individual:
            mhp = float(m.get("home_prob", 0.33))
            mdp = float(m.get("draw_prob", 0.33))
            map_ = float(m.get("away_prob", 0.33))
            wt   = float(m.get("model_weight", 1.0))
            cal  = m.get("calibration", {})
            breakdown.append({
                "model_name":       m.get("model_name"),
                "model_type":       m.get("model_type"),
                "weight":           wt,
                "home_prob":        mhp,
                "draw_prob":        mdp,
                "away_prob":        map_,
                "delta_home":       round(mhp - ensemble_hp, 4),
                "delta_draw":       round(mdp - ensemble_dp, 4),
                "delta_away":       round(map_ - ensemble_ap, 4),
                "over_2_5_prob":    m.get("over_2_5_prob"),
                "btts_prob":        m.get("btts_prob"),
                "confidence":       m.get("confidence", {}),
                "calibration_applied": bool(cal.get("applied")),
                "calibration_method":  cal.get("method"),
                "supported_markets":   m.get("supported_markets", []),
            })

        return {
            "match_id":     match_id,
            "audit_id":     audit.id,
            "created_at":   audit.created_at,
            "triggered_by": audit.triggered_by,
            "ensemble": {
                "home_prob":       ensemble_hp,
                "draw_prob":       ensemble_dp,
                "away_prob":       ensemble_ap,
                "confidence":      audit.confidence,
                "risk_score":      audit.risk_score,
                "model_agreement": audit.model_agreement,
            },
            "models_count": len(breakdown),
            "breakdown":    breakdown,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[breakdown] match_id=%s error: %s", match_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── P3#13: Walk-forward backtest ──────────────────────────────────────────────

@router.get("/backtest/walk-forward")
async def walk_forward_backtest(
    days_back:  int = Query(30,  ge=1,  le=365, description="Historical window in days"),
    step_size:  int = Query(7,   ge=1,  le=30,  description="Step size in days for rolling window"),
    min_window: int = Query(14,  ge=7,  le=90,  description="Minimum training window in days"),
    db: AsyncSession = Depends(get_db),
):
    """
    P3#13 — Walk-forward backtesting.

    Rolls a training window forward in steps of `step_size` days over the
    last `days_back` days of settled predictions.  For each window, computes
    per-model accuracy, log-loss, and Brier score.

    Returns a time-series of performance snapshots suitable for plotting
    model accuracy over time.
    """
    from datetime import datetime, timedelta, timezone
    from app.modules.ai.models import AIPredictionAudit
    from app.db.models import Match

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    # Fetch settled audits
    result = await db.execute(
        select(AIPredictionAudit, Match)
        .join(Match, AIPredictionAudit.match_id == cast(Match.id, String))
        .where(
            and_(
                AIPredictionAudit.created_at >= cutoff,
                Match.actual_outcome.isnot(None),
            )
        )
        .order_by(AIPredictionAudit.created_at)
    )
    rows = result.all()

    if not rows:
        # Fallback: query audits without join and try to get outcome
        audit_res = await db.execute(
            select(AIPredictionAudit)
            .where(AIPredictionAudit.created_at >= cutoff)
            .order_by(AIPredictionAudit.created_at)
        )
        audits = audit_res.scalars().all()
        if not audits:
            return {"steps": [], "total_samples": 0, "message": "No settled predictions found"}

        # Build steps from audits alone (without outcome join)
        return {
            "steps": [],
            "total_samples": len(audits),
            "message": "Walk-forward requires settled outcomes; found audits but no linked outcomes",
        }

    # Build step windows
    steps = []
    all_dates = [r.AIPredictionAudit.created_at for r in rows]
    start_date = all_dates[0]
    end_date   = all_dates[-1]

    window_start = start_date
    while window_start < end_date:
        window_end = window_start + timedelta(days=step_size)
        train_rows = [r for r in rows if r.AIPredictionAudit.created_at < window_start]
        test_rows  = [r for r in rows if window_start <= r.AIPredictionAudit.created_at < window_end]

        if len(test_rows) < 3:
            window_start = window_end
            continue

        # Per-model stats for this step
        model_stats: Dict[str, Dict] = {}
        for row in test_rows:
            audit   = row.AIPredictionAudit
            match   = row.Match
            outcome = (match.actual_outcome or "").upper()
            if outcome not in ("H", "D", "A"):
                continue

            for m in (audit.individual_results or []):
                mn   = m.get("model_name", "unknown")
                mhp  = float(m.get("home_prob", 0.33))
                mdp  = float(m.get("draw_prob", 0.33))
                map_ = float(m.get("away_prob", 0.33))
                pred = max(("H", mhp), ("D", mdp), ("A", map_), key=lambda x: x[1])[0]
                true_p = {"H": mhp, "D": mdp, "A": map_}.get(outcome, 0.33)
                truth  = {"H": (1,0,0), "D": (0,1,0), "A": (0,0,1)}.get(outcome, (0,0,0))
                brier  = sum((p - t)**2 for p, t in zip((mhp, mdp, map_), truth)) / 3.0
                ll     = -math.log(max(true_p, 1e-9))

                if mn not in model_stats:
                    model_stats[mn] = {"correct": 0, "n": 0, "ll": 0.0, "brier": 0.0}
                s = model_stats[mn]
                s["n"]      += 1
                s["correct"] += 1 if pred == outcome else 0
                s["ll"]     += ll
                s["brier"]  += brier

        step_models = [
            {
                "model_name": mn,
                "n":          s["n"],
                "accuracy":   round(s["correct"] / s["n"], 4) if s["n"] > 0 else None,
                "log_loss":   round(s["ll"] / s["n"], 4)      if s["n"] > 0 else None,
                "brier":      round(s["brier"] / s["n"], 4)   if s["n"] > 0 else None,
            }
            for mn, s in model_stats.items()
        ]

        steps.append({
            "window_start": window_start.isoformat(),
            "window_end":   window_end.isoformat(),
            "train_samples": len(train_rows),
            "test_samples":  len(test_rows),
            "models":        step_models,
        })
        window_start = window_end

    return {
        "steps":         steps,
        "total_samples": len(rows),
        "days_back":     days_back,
        "step_size":     step_size,
    }


# ── P3#14: Model attribution ──────────────────────────────────────────────────

@router.get("/predictions/{match_id}/attribution")
async def get_model_attribution(
    match_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    P3#14 — Return how much each model shifted the ensemble prediction
    for a specific match.

    Uses the `attribution` field from the raw orchestrator output, which is
    stored in the AIPredictionAudit weights_snapshot (v5 extended).  Falls
    back to reconstructing attribution from individual_results if the
    direct attribution field is absent.
    """
    try:
        from app.modules.ai.models import AIPredictionAudit
        result = await db.execute(
            select(AIPredictionAudit)
            .where(AIPredictionAudit.match_id == str(match_id))
            .order_by(desc(AIPredictionAudit.created_at))
            .limit(1)
        )
        audit = result.scalar_one_or_none()
        if audit is None:
            raise HTTPException(status_code=404, detail=f"No prediction audit found for match_id={match_id}")

        ensemble_hp = float(audit.home_prob or 0.33)
        ensemble_dp = float(audit.draw_prob or 0.33)
        ensemble_ap = float(audit.away_prob or 0.33)

        individual = audit.individual_results or []
        weights_snap = audit.weights_snapshot or {}

        # Reconstruct attribution from individual results + weights
        total_w = sum(float(m.get("model_weight", 1.0)) for m in individual)
        if total_w <= 0:
            total_w = 1.0

        attribution = []
        for m in individual:
            mn   = m.get("model_name", "unknown")
            key  = m.get("model_type", mn)
            wt   = float(m.get("model_weight", 1.0))
            mhp  = float(m.get("home_prob", ensemble_hp))
            mdp  = float(m.get("draw_prob", ensemble_dp))
            map_ = float(m.get("away_prob", ensemble_ap))
            w_frac = wt / total_w

            attribution.append({
                "model_name":  mn,
                "model_key":   key,
                "weight":      round(wt, 4),
                "weight_frac": round(w_frac, 4),
                "home_prob":   round(mhp, 4),
                "draw_prob":   round(mdp, 4),
                "away_prob":   round(map_, 4),
                "delta_home":  round((mhp - ensemble_hp) * w_frac, 5),
                "delta_draw":  round((mdp - ensemble_dp) * w_frac, 5),
                "delta_away":  round((map_ - ensemble_ap) * w_frac, 5),
                "abs_delta":   round(abs(mhp - ensemble_hp) * w_frac, 5),
            })

        # Sort by absolute impact descending
        attribution.sort(key=lambda x: x["abs_delta"], reverse=True)

        return {
            "match_id":  match_id,
            "audit_id":  audit.id,
            "ensemble":  {"home_prob": ensemble_hp, "draw_prob": ensemble_dp, "away_prob": ensemble_ap},
            "attribution": attribution,
            "models_count": len(attribution),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[attribution] match_id=%s error: %s", match_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── P1#6: Score-conditional live recalculation ────────────────────────────────

@router.post("/predict/live-score")
async def predict_live_score(
    body: LiveScoreRequest,
    orchestrator = Depends(get_orchestrator_dep),
):
    """
    P1#6 — Score-conditional live recalculation.

    Given the current scoreline and minute, recalculates win probabilities
    using Poisson xG adjusted for the remaining match time and goal state.

    Does NOT require a DB match record — works purely from provided market odds.
    """
    try:
        mkt = body.market_odds or {"home": 2.30, "draw": 3.30, "away": 3.10}
        features = {
            "home_team":   body.home_team,
            "away_team":   body.away_team,
            "league":      body.league,
            "market_odds": mkt,
        }
        result = orchestrator.predict_with_scoreline(
            features   = features,
            match_id   = str(body.match_id or "live"),
            home_score = body.home_score,
            away_score = body.away_score,
            minute     = body.minute,
        )
        return {
            "match":   f"{body.home_team} vs {body.away_team}",
            "scoreline": f"{body.home_score}-{body.away_score}",
            **result,
        }
    except Exception as exc:
        logger.error("[live-score] error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
