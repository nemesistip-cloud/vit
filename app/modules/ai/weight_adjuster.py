# app/modules/ai/weight_adjuster.py
"""
E3 — Model Weight Adjuster

After each match settles, compare each model's predicted probability
against the actual outcome and update its weight:

    new_weight = old_weight × (1 + performance_delta × learning_rate)

Rules:
- Correct prediction (outcome matches argmax)  → +performance_delta
- Wrong prediction                             → -performance_delta
- Weights are clamped to [MIN_WEIGHT, MAX_WEIGHT]
- Changes are written to ModelMetadata and synced to the orchestrator

Called by the auto-settle loop in main.py after settle_results() returns
and also available as a standalone admin trigger.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import AIPredictionAudit, ModelMetadata
from app.services.accuracy_enhancer import compute_log_loss_delta, log_loss_for_outcome

logger = logging.getLogger(__name__)

LEARNING_RATE  = 0.05   # how fast weights change per settled match
PERFORMANCE_DELTA = 0.10   # base delta applied each correct/wrong match
MIN_WEIGHT     = 0.10   # floor — bad models still contribute a little
MAX_WEIGHT     = 5.00   # ceiling — star models don't dominate completely
ACCURACY_WINDOW = 50    # rolling window for accuracy calculation


async def adjust_weights_for_match(
    db: AsyncSession,
    orchestrator: Any,
    match_id: str,
    actual_outcome: str,     # "home" | "draw" | "away"
) -> Dict[str, Any]:
    """
    Adjust model weights based on the settled outcome for one match.
    Updates ModelMetadata rows and pushes new weights to live orchestrator.
    """
    if actual_outcome not in ("home", "draw", "away"):
        return {"error": f"Unknown outcome: {actual_outcome}"}

    # Pull the most recent audit entry for this match
    result = await db.execute(
        select(AIPredictionAudit)
        .where(AIPredictionAudit.match_id == str(match_id))
        .order_by(AIPredictionAudit.created_at.desc())
        .limit(1)
    )
    audit: Optional[AIPredictionAudit] = result.scalar_one_or_none()

    if audit is None or not audit.individual_results:
        logger.info(f"[weight_adjuster] No audit record for match {match_id} — skipping")
        return {"match_id": match_id, "adjusted": 0, "reason": "no_audit_record"}

    individual: List[Dict] = audit.individual_results
    outcome_map = {"home": "home_prob", "draw": "draw_prob", "away": "away_prob"}
    target_key = outcome_map[actual_outcome]

    adjustments: List[Dict] = []

    for model_pred in individual:
        model_name = model_pred.get("model_name", "")

        # Find the registry key by name
        reg_result = await db.execute(
            select(ModelMetadata).where(ModelMetadata.name == model_name)
        )
        reg_row: Optional[ModelMetadata] = reg_result.scalar_one_or_none()
        if reg_row is None:
            continue

        # Determine if prediction was correct (argmax matches actual)
        hp = model_pred.get("home_prob", 0.33)
        dp = model_pred.get("draw_prob", 0.33)
        ap = model_pred.get("away_prob", 0.34)

        argmax_key = max(
            [("home", hp), ("draw", dp), ("away", ap)],
            key=lambda x: x[1],
        )[0]
        correct = argmax_key == actual_outcome

        # Brier contribution for this model
        prob_correct = float(model_pred.get(target_key, 0.33))
        brier_contrib = (prob_correct - 1.0) ** 2  # lower is better

        # Log-loss contribution (proper scoring rule)
        nll_contrib = log_loss_for_outcome(hp, dp, ap, actual_outcome)

        # Weight update — magnitude scales with how confident & how right/wrong
        # the model was, instead of a flat ±10% based on argmax alone.
        delta = compute_log_loss_delta(prob_correct, base_delta=PERFORMANCE_DELTA)
        old_weight = reg_row.weight
        new_weight = old_weight * (1 + delta * LEARNING_RATE)
        new_weight = round(max(MIN_WEIGHT, min(MAX_WEIGHT, new_weight)), 6)

        # Update accuracy counters
        reg_row.predictions_total = (reg_row.predictions_total or 0) + 1
        if correct:
            reg_row.predictions_correct = (reg_row.predictions_correct or 0) + 1

        total = reg_row.predictions_total
        correct_total = reg_row.predictions_correct
        reg_row.accuracy_1x2 = round(correct_total / total, 4) if total else None

        # Rolling Brier + log-loss (exponential moving average)
        alpha = 2 / (ACCURACY_WINDOW + 1)
        old_brier = reg_row.brier_score or 0.25
        reg_row.brier_score = round(alpha * brier_contrib + (1 - alpha) * old_brier, 4)
        old_nll = reg_row.log_loss or math.log(3.0)
        reg_row.log_loss = round(alpha * nll_contrib + (1 - alpha) * old_nll, 4)

        reg_row.weight = new_weight

        # Also push into live orchestrator immediately
        if reg_row.key in orchestrator.model_meta:
            orchestrator.model_meta[reg_row.key]["weight"] = new_weight

        adjustments.append({
            "model_key":  reg_row.key,
            "model_name": model_name,
            "correct":    correct,
            "p_actual":   round(prob_correct, 4),
            "delta":      round(delta, 6),
            "old_weight": old_weight,
            "new_weight": new_weight,
            "accuracy":   reg_row.accuracy_1x2,
            "brier":      reg_row.brier_score,
            "log_loss":   reg_row.log_loss,
        })

    await db.commit()

    logger.info(
        f"[weight_adjuster] match={match_id} outcome={actual_outcome} "
        f"adjusted={len(adjustments)} models"
    )

    return {
        "match_id":   match_id,
        "outcome":    actual_outcome,
        "adjusted":   len(adjustments),
        "models":     adjustments,
    }


async def run_bulk_weight_adjustment(
    db: AsyncSession,
    orchestrator: Any,
    days_back: int = 7,
) -> Dict[str, Any]:
    """
    Bulk re-run weight adjustment for all recently settled matches
    that have an audit record.  Useful for initial calibration or
    after uploading a new .pkl file.
    """
    from datetime import timedelta
    from sqlalchemy import and_
    from app.db.models import Match

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    result = await db.execute(
        select(Match)
        .where(
            and_(
                Match.actual_outcome.isnot(None),
                Match.updated_at >= cutoff,
            )
        )
    )
    settled_matches = result.scalars().all()

    total_adjusted = 0
    summary = []

    for match in settled_matches:
        match_id = str(match.external_id or match.id)
        adj = await adjust_weights_for_match(
            db, orchestrator, match_id, match.actual_outcome
        )
        total_adjusted += adj.get("adjusted", 0)
        summary.append({"match_id": match_id, "adjusted": adj.get("adjusted", 0)})

    return {
        "days_back":    days_back,
        "matches_processed": len(settled_matches),
        "total_weight_updates": total_adjusted,
        "summary": summary,
    }


async def get_model_performance_report(db: AsyncSession) -> List[Dict]:
    """Return a ranked performance report for all registered models."""
    result = await db.execute(
        select(ModelMetadata).order_by(ModelMetadata.weight.desc())
    )
    rows = result.scalars().all()

    report = []
    for r in rows:
        total = r.predictions_total or 0
        correct = r.predictions_correct or 0
        report.append({
            "key":                r.key,
            "name":               r.name,
            "weight":             r.weight,
            "accuracy_1x2":       r.accuracy_1x2,
            "brier_score":        r.brier_score,
            "predictions_total":  total,
            "predictions_correct": correct,
            "win_rate":           round(correct / total, 4) if total else None,
            "pkl_loaded":         r.pkl_loaded,
            "is_active":          r.is_active,
        })
    return report
