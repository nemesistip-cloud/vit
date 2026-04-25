# app/modules/ai/weight_adjuster.py
"""
E3 — Model Weight Adjuster

After each match settles, compare each model's predicted probability
against the actual outcome and update its weight:

    loss_delta = compute_log_loss_delta(prob_assigned_to_actual)
    clv_delta  = clv * (model_prob_for_bet_side - market_prob_for_bet_side)
    final_delta = (1 - CLV_WEIGHT) * loss_delta + CLV_WEIGHT * clv_signal
    new_weight = old_weight × (1 + final_delta × learning_rate)

The CLV signal is the leading indicator: a model that consistently puts
probability on the side that *beats the closing line* is rewarded even
on losing bets, because positive CLV is the only proven proxy for true
edge in betting markets. Settlement accuracy alone is high-variance and
lagging.

Rules:
- Weights are clamped to [MIN_WEIGHT, MAX_WEIGHT]
- CLV blending only fires when a CLVEntry exists for the match; otherwise
  the loop falls back to pure log-loss-driven updates (backward compatible)
- Changes are written to ModelMetadata and synced to the orchestrator

Called by the auto-settle loop in main.py after settle_results() returns
(which populates CLVEntry.closing_odds and CLVEntry.clv inline) and also
available as a standalone admin trigger.
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

# CLV blending — the single biggest leverage in the weight loop.
# 0.0 = pure log-loss (legacy behaviour); 1.0 = pure CLV.
# 0.4 means CLV contributes ~40% of the weight signal once a CLVEntry exists.
CLV_WEIGHT     = 0.40
CLV_GAIN       = 5.00   # scale factor — CLV is typically in [-0.10, +0.15]; gain pushes it onto the same magnitude as log-loss delta
CLV_MAX_DELTA  = 0.50   # safety clamp on the per-match CLV-driven delta


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

    # ── CLV signal lookup ─────────────────────────────────────────────────
    # Pull any CLVEntry for this match (settler populates closing_odds + clv inline).
    # CLV is the same for every model — what differs is each model's probability
    # alignment with the bet_side, which is how we attribute credit/blame.
    clv_value: Optional[float] = None
    clv_bet_side: Optional[str] = None
    clv_market_prob: Optional[float] = None
    try:
        from app.db.models import CLVEntry, Match  # local import — avoids circular deps at module load

        # Resolve numeric match.id from external id when needed
        match_pk: Optional[int] = None
        try:
            match_pk = int(match_id)
        except (TypeError, ValueError):
            mres = await db.execute(
                select(Match.id).where(Match.external_id == str(match_id))
            )
            match_pk = mres.scalar_one_or_none()

        if match_pk is not None:
            cres = await db.execute(
                select(CLVEntry)
                .where(CLVEntry.match_id == match_pk)
                .where(CLVEntry.clv.isnot(None))
                .order_by(CLVEntry.timestamp.desc())
                .limit(1)
            )
            clv_row = cres.scalar_one_or_none()
            if clv_row is not None:
                clv_value = float(clv_row.clv)
                clv_bet_side = clv_row.bet_side
                # Implied closing-line probability for the bet side (vig-included is fine
                # for relative-attribution use; we're scoring "did the model agree with
                # the side that beat the line", not absolute calibration).
                if clv_row.closing_odds and clv_row.closing_odds > 0:
                    clv_market_prob = 1.0 / float(clv_row.closing_odds)
    except Exception as _clv_e:
        logger.warning(f"[weight_adjuster] CLV lookup failed for match={match_id}: {_clv_e}")

    clv_signal_active = (
        clv_value is not None
        and clv_bet_side in ("home", "draw", "away")
        and clv_market_prob is not None
    )

    adjustments: List[Dict] = []

    for model_pred in individual:
        model_name = model_pred.get("model_name", "")

        # Find the active registry row by name. Since v4.6 the same display name
        # ("XGBoost", "PoissonGoals", ...) exists for both *_v1 and *_v2 rows;
        # bootstrap deactivates v1 once v2 is registered, so we filter on
        # is_active=True and fall back to most-recent if ambiguity remains.
        reg_result = await db.execute(
            select(ModelMetadata)
            .where(ModelMetadata.name == model_name)
            .where(ModelMetadata.is_active.is_(True))
            .order_by(ModelMetadata.id.desc())
            .limit(1)
        )
        reg_row: Optional[ModelMetadata] = reg_result.scalar_one_or_none()
        if reg_row is None:
            # Fallback for legacy datasets where v1 was deactivated then v2
            # never registered — pick any matching row.
            fallback = await db.execute(
                select(ModelMetadata)
                .where(ModelMetadata.name == model_name)
                .order_by(ModelMetadata.id.desc())
                .limit(1)
            )
            reg_row = fallback.scalar_one_or_none()
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

        # Base delta from log-loss — magnitude scales with confidence & correctness
        loss_delta = compute_log_loss_delta(prob_correct, base_delta=PERFORMANCE_DELTA)

        # ── CLV-blended delta ─────────────────────────────────────────────
        # Reward models that put more probability than the market on the side
        # that beat the closing line; penalise models that disagreed with a
        # winning CLV bet. This is the leading indicator the legacy loop missed.
        clv_delta = 0.0
        clv_attribution = 0.0  # per-model CLV contribution stored as rolling EMA
        if clv_signal_active:
            side_prob_key = outcome_map[clv_bet_side]
            model_side_prob = float(model_pred.get(side_prob_key, 0.33))
            prob_alignment = model_side_prob - clv_market_prob  # >0 = model was sharper than market on this side
            # raw_clv_delta lives in roughly [-CLV_GAIN, +CLV_GAIN] before clamping
            raw_clv_delta = clv_value * prob_alignment * CLV_GAIN
            clv_delta = max(-CLV_MAX_DELTA, min(CLV_MAX_DELTA, raw_clv_delta))
            clv_attribution = clv_value * prob_alignment  # un-amplified for the rolling stat

            final_delta = (1.0 - CLV_WEIGHT) * loss_delta + CLV_WEIGHT * clv_delta
        else:
            final_delta = loss_delta

        old_weight = reg_row.weight
        new_weight = old_weight * (1 + final_delta * LEARNING_RATE)
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

        # Rolling CLV score — only updated when a CLV signal was available.
        # Positive values = model consistently beats the closing line.
        if clv_signal_active:
            old_clv = reg_row.clv_score if reg_row.clv_score is not None else 0.0
            reg_row.clv_score = round(alpha * clv_attribution + (1 - alpha) * old_clv, 6)
            reg_row.clv_samples = (reg_row.clv_samples or 0) + 1

        reg_row.weight = new_weight

        # Also push into live orchestrator immediately
        if reg_row.key in orchestrator.model_meta:
            orchestrator.model_meta[reg_row.key]["weight"] = new_weight

        adjustments.append({
            "model_key":  reg_row.key,
            "model_name": model_name,
            "correct":    correct,
            "p_actual":   round(prob_correct, 4),
            "loss_delta": round(loss_delta, 6),
            "clv_delta":  round(clv_delta, 6) if clv_signal_active else None,
            "delta":      round(final_delta, 6),
            "old_weight": old_weight,
            "new_weight": new_weight,
            "accuracy":   reg_row.accuracy_1x2,
            "brier":      reg_row.brier_score,
            "log_loss":   reg_row.log_loss,
            "clv_score":  reg_row.clv_score,
        })

    await db.commit()

    if clv_signal_active:
        logger.info(
            f"[weight_adjuster] match={match_id} outcome={actual_outcome} "
            f"adjusted={len(adjustments)} models | CLV={clv_value:+.4f} bet_side={clv_bet_side} "
            f"market_p={clv_market_prob:.3f}"
        )
    else:
        logger.info(
            f"[weight_adjuster] match={match_id} outcome={actual_outcome} "
            f"adjusted={len(adjustments)} models | CLV unavailable (log-loss only)"
        )

    return {
        "match_id":      match_id,
        "outcome":       actual_outcome,
        "adjusted":      len(adjustments),
        "clv_active":    clv_signal_active,
        "clv_value":     clv_value,
        "clv_bet_side":  clv_bet_side,
        "models":        adjustments,
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
            "log_loss":           r.log_loss,
            "clv_score":          r.clv_score,
            "clv_samples":        r.clv_samples or 0,
            "clv_negative_streak_days": getattr(r, "clv_negative_streak_days", 0) or 0,
            "last_clv_check_at":  r.last_clv_check_at.isoformat() if getattr(r, "last_clv_check_at", None) else None,
            "auto_demoted":       bool(getattr(r, "auto_demoted", False)),
            "predictions_total":  total,
            "predictions_correct": correct,
            "win_rate":           round(correct / total, 4) if total else None,
            "pkl_loaded":         r.pkl_loaded,
            "is_active":          r.is_active,
        })
    return report
