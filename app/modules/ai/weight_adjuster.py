# app/modules/ai/weight_adjuster.py
"""
E3 — Model Weight Adjuster  (v2 — improved scoring + normalization)

After each match settles, compare each model's predicted probability
against the actual outcome and update its weight:

    brier    = multi-class Brier score  ((hp-ht)²+(dp-dt)²+(ap-at)²) / 3
    loss_delta = compute_log_loss_delta(prob_assigned_to_actual)
    clv_delta  = clv × (model_prob_for_bet_side − market_prob) × CLV_GAIN
    final_delta = (1 − CLV_WEIGHT) × loss_delta + CLV_WEIGHT × clv_delta
    new_weight  = old_weight × (1 + final_delta × effective_lr)

Improvements over v1:
  - Multi-class Brier (all three outcome classes, not just the actual one)
  - Adaptive learning rate: scales down as the model accumulates samples
    (high early, decays toward MIN_LR as N grows) — prevents over-fitting
    to single results early on while still allowing fast adjustment
  - Soft regularization: weights are gently pulled toward 1.0 each update
    so the ensemble mean stays stable over time
  - CLV gated on minimum sample count (no CLV blending until 10+ predictions)
  - Post-update ensemble normalization: after all models are updated for a
    match, scale so the mean weight = 1.0 (prevents runaway weight drift)

Called by the auto-settle loop in main.py and available as admin trigger.
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

# ── Hyperparameters ────────────────────────────────────────────────────────────
MAX_LEARNING_RATE  = 0.10    # LR applied to first few predictions (fast adaptation)
MIN_LEARNING_RATE  = 0.02    # LR floor after many predictions      (slow, stable)
LR_DECAY_SAMPLES   = 100     # N at which LR has decayed halfway to MIN_LR

PERFORMANCE_DELTA  = 0.10    # base delta magnitude for log-loss scoring
REGULARIZATION     = 0.005   # soft pull toward weight=1.0 each update (prevents drift)

MIN_WEIGHT         = 0.10    # floor — bad models still contribute a little
MAX_WEIGHT         = 5.00    # ceiling — star models don't dominate completely
ACCURACY_WINDOW    = 50      # EMA window for rolling Brier / log-loss
CLV_MIN_SAMPLES    = 10      # minimum predictions before CLV blending fires

# CLV blending — the single biggest leverage in the weight loop.
CLV_WEIGHT         = 0.40    # fraction of final_delta from CLV signal
CLV_GAIN           = 5.00    # scale factor (CLV ≈ [-0.10,+0.15]; gain → same magnitude as log-loss)
CLV_MAX_DELTA      = 0.50    # safety clamp on per-match CLV-driven delta

# Bootstrap: minimum live predictions before we consider metrics "live".
# Below this threshold, metrics are either bootstrapped or from training data.
BOOTSTRAP_LIVE_THRESHOLD = 5

# ── Model-type priors ──────────────────────────────────────────────────────────
# Calibrated typical ranges for 1X2 football prediction based on published ML
# benchmarks.  Used as EMA warm-start for models with insufficient live data.
# Keys must match ModelMetadata.model_type (case-insensitive).
_TYPE_PRIORS: Dict[str, Dict[str, float]] = {
    "market_implied":      {"accuracy": 0.700, "brier": 0.210, "log_loss": 0.720},
    "neural_ensemble":     {"accuracy": 0.640, "brier": 0.228, "log_loss": 0.820},
    "xgboost":             {"accuracy": 0.620, "brier": 0.238, "log_loss": 0.860},
    "hybrid_stack":        {"accuracy": 0.630, "brier": 0.232, "log_loss": 0.840},
    "hybrid":              {"accuracy": 0.630, "brier": 0.232, "log_loss": 0.840},
    "transformer":         {"accuracy": 0.610, "brier": 0.240, "log_loss": 0.870},
    "lstm":                {"accuracy": 0.600, "brier": 0.244, "log_loss": 0.880},
    "poisson_goals":       {"accuracy": 0.580, "brier": 0.250, "log_loss": 0.910},
    "dixon_coles":         {"accuracy": 0.590, "brier": 0.248, "log_loss": 0.900},
    "bayesian_net":        {"accuracy": 0.590, "brier": 0.247, "log_loss": 0.895},
    "random_forest":       {"accuracy": 0.600, "brier": 0.244, "log_loss": 0.882},
    "elo_rating":          {"accuracy": 0.570, "brier": 0.255, "log_loss": 0.930},
    "logistic_regression": {"accuracy": 0.560, "brier": 0.258, "log_loss": 0.950},
}
_DEFAULT_PRIOR: Dict[str, float] = {"accuracy": 0.580, "brier": 0.260, "log_loss": 0.950}


def _get_type_prior(model_type: str) -> Dict[str, float]:
    """Return the benchmark prior for a given model_type (case-insensitive)."""
    key = (model_type or "").lower().replace("-", "_").replace(" ", "_")
    return dict(_TYPE_PRIORS.get(key, _DEFAULT_PRIOR))


def _effective_lr(n_predictions: int) -> float:
    """
    Adaptive learning rate that starts at MAX_LR and decays toward MIN_LR.
    Uses exponential decay: lr = MIN_LR + (MAX_LR - MIN_LR) / (1 + n / LR_DECAY_SAMPLES)
    """
    return MIN_LEARNING_RATE + (MAX_LEARNING_RATE - MIN_LEARNING_RATE) / (
        1.0 + n_predictions / LR_DECAY_SAMPLES
    )


def _multi_class_brier(hp: float, dp: float, ap: float, actual_outcome: str) -> float:
    """
    Proper multi-class Brier score: mean squared error over all three outcome
    probabilities. Range [0, 2]; lower is better. A random model scores ≈0.444.
    """
    h_true = 1.0 if actual_outcome == "home" else 0.0
    d_true = 1.0 if actual_outcome == "draw" else 0.0
    a_true = 1.0 if actual_outcome == "away" else 0.0
    return ((hp - h_true) ** 2 + (dp - d_true) ** 2 + (ap - a_true) ** 2) / 3.0


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

    # ── CLV signal lookup ─────────────────────────────────────────────────────
    clv_value: Optional[float] = None
    clv_bet_side: Optional[str] = None
    clv_market_prob: Optional[float] = None
    try:
        from app.db.models import CLVEntry, Match

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
                if clv_row.closing_odds and clv_row.closing_odds > 0:
                    clv_market_prob = 1.0 / float(clv_row.closing_odds)
    except Exception as _clv_e:
        logger.warning(f"[weight_adjuster] CLV lookup failed for match={match_id}: {_clv_e}")

    adjustments: List[Dict] = []
    updated_reg_rows: List[ModelMetadata] = []

    for model_pred in individual:
        model_name = model_pred.get("model_name", "")

        reg_result = await db.execute(
            select(ModelMetadata)
            .where(ModelMetadata.name == model_name)
            .where(ModelMetadata.is_active.is_(True))
            .order_by(ModelMetadata.id.desc())
            .limit(1)
        )
        reg_row: Optional[ModelMetadata] = reg_result.scalar_one_or_none()
        if reg_row is None:
            fallback = await db.execute(
                select(ModelMetadata)
                .where(ModelMetadata.name == model_name)
                .order_by(ModelMetadata.id.desc())
                .limit(1)
            )
            reg_row = fallback.scalar_one_or_none()
            if reg_row is None:
                continue

        hp = float(model_pred.get("home_prob", 0.33))
        dp = float(model_pred.get("draw_prob", 0.33))
        ap = float(model_pred.get("away_prob", 0.34))

        argmax_key = max(
            [("home", hp), ("draw", dp), ("away", ap)],
            key=lambda x: x[1],
        )[0]
        correct = argmax_key == actual_outcome

        # ── Scoring ───────────────────────────────────────────────────────────
        # Multi-class Brier (proper — penalises all three probability assignments)
        brier_contrib = _multi_class_brier(hp, dp, ap, actual_outcome)

        # Full log-loss for the match (proper scoring rule)
        nll_contrib = log_loss_for_outcome(hp, dp, ap, actual_outcome)

        # Primary performance delta (from log-loss relative to uniform baseline)
        prob_correct = float(model_pred.get(target_key, 0.33))
        loss_delta = compute_log_loss_delta(prob_correct, base_delta=PERFORMANCE_DELTA)

        # ── CLV-blended delta ─────────────────────────────────────────────────
        n_preds = (reg_row.predictions_total or 0) + 1   # +1 for current match
        clv_signal_active = (
            clv_value is not None
            and clv_bet_side in ("home", "draw", "away")
            and clv_market_prob is not None
            and n_preds >= CLV_MIN_SAMPLES   # wait for minimum sample base
        )

        clv_delta = 0.0
        clv_attribution = 0.0
        if clv_signal_active:
            side_prob_key = outcome_map[clv_bet_side]
            model_side_prob = float(model_pred.get(side_prob_key, 0.33))
            prob_alignment = model_side_prob - clv_market_prob
            raw_clv_delta = clv_value * prob_alignment * CLV_GAIN
            clv_delta = max(-CLV_MAX_DELTA, min(CLV_MAX_DELTA, raw_clv_delta))
            clv_attribution = clv_value * prob_alignment

            final_delta = (1.0 - CLV_WEIGHT) * loss_delta + CLV_WEIGHT * clv_delta
        else:
            final_delta = loss_delta

        # ── Adaptive LR + soft regularization ────────────────────────────────
        lr = _effective_lr(n_preds)

        old_weight = float(reg_row.weight or 1.0)

        # Soft pull toward 1.0 (regularization prevents runaway weight drift)
        regularized_weight = old_weight * (1.0 - REGULARIZATION) + REGULARIZATION

        new_weight = regularized_weight * (1.0 + final_delta * lr)
        new_weight = round(max(MIN_WEIGHT, min(MAX_WEIGHT, new_weight)), 6)

        # ── Update accuracy counters ──────────────────────────────────────────
        reg_row.predictions_total = (reg_row.predictions_total or 0) + 1
        if correct:
            reg_row.predictions_correct = (reg_row.predictions_correct or 0) + 1

        total = reg_row.predictions_total
        correct_total = reg_row.predictions_correct
        reg_row.accuracy_1x2 = round(correct_total / total, 4) if total else None

        # Adaptive EMA: give early samples more weight, stabilise later
        # alpha decays from ~0.4 (first few preds) toward 2/(WINDOW+1) ≈ 0.038
        alpha_fixed = 2.0 / (ACCURACY_WINDOW + 1)
        alpha = max(alpha_fixed, 2.0 / (total + 1)) if total < ACCURACY_WINDOW else alpha_fixed

        # EMA warm-start: use type-prior as fallback if no value set yet
        # (avoids starting from the useless random baseline of 0.444 / log(3))
        _prior = _get_type_prior(getattr(reg_row, "model_type", "") or "")
        old_brier = float(reg_row.brier_score) if reg_row.brier_score is not None else _prior["brier"]
        reg_row.brier_score = round(alpha * brier_contrib + (1 - alpha) * old_brier, 5)

        old_nll = float(reg_row.log_loss) if reg_row.log_loss is not None else _prior["log_loss"]
        reg_row.log_loss = round(alpha * nll_contrib + (1 - alpha) * old_nll, 5)

        if clv_signal_active:
            old_clv = float(reg_row.clv_score or 0.0) if reg_row.clv_score is not None else 0.0
            reg_row.clv_score = round(alpha * clv_attribution + (1 - alpha) * old_clv, 6)
            reg_row.clv_samples = (reg_row.clv_samples or 0) + 1

        reg_row.weight = new_weight
        updated_reg_rows.append(reg_row)

        adjustments.append({
            "model_key":     reg_row.key,
            "model_name":    model_name,
            "correct":       correct,
            "p_actual":      round(prob_correct, 4),
            "brier":         round(brier_contrib, 5),
            "loss_delta":    round(loss_delta, 6),
            "clv_delta":     round(clv_delta, 6) if clv_signal_active else None,
            "delta":         round(final_delta, 6),
            "lr":            round(lr, 5),
            "old_weight":    round(old_weight, 6),
            "new_weight":    new_weight,
            "accuracy":      reg_row.accuracy_1x2,
            "brier_ema":     reg_row.brier_score,
            "log_loss_ema":  reg_row.log_loss,
            "clv_score":     reg_row.clv_score,
        })

    # ── Post-update ensemble normalization ───────────────────────────────────
    # Scale all updated weights so their mean = 1.0.
    # This keeps the ensemble balanced: no runaway drift regardless of streak.
    if updated_reg_rows:
        weights = [float(r.weight) for r in updated_reg_rows]
        mean_w = sum(weights) / len(weights)
        if mean_w > 0 and abs(mean_w - 1.0) > 0.02:   # only normalize if >2% off
            scale = 1.0 / mean_w
            for row, adj in zip(updated_reg_rows, adjustments):
                norm_weight = round(max(MIN_WEIGHT, min(MAX_WEIGHT, row.weight * scale)), 6)
                adj["norm_weight"] = norm_weight
                adj["new_weight"]  = norm_weight
                row.weight = norm_weight
                if row.key in orchestrator.model_meta:
                    orchestrator.model_meta[row.key]["weight"] = norm_weight
            logger.debug(f"[weight_adjuster] Normalized weights (mean was {mean_w:.4f})")
        else:
            # Push weights to orchestrator without rescaling
            for row in updated_reg_rows:
                if row.key in orchestrator.model_meta:
                    orchestrator.model_meta[row.key]["weight"] = row.weight

    await db.commit()

    clv_signal_active_any = any(a["clv_delta"] is not None for a in adjustments)
    if clv_signal_active_any:
        logger.info(
            f"[weight_adjuster] match={match_id} outcome={actual_outcome} "
            f"adjusted={len(adjustments)} models | CLV={clv_value:+.4f} side={clv_bet_side} "
            f"market_p={clv_market_prob:.3f}"
        )
    else:
        logger.info(
            f"[weight_adjuster] match={match_id} outcome={actual_outcome} "
            f"adjusted={len(adjustments)} models | log-loss only (CLV unavailable or <{CLV_MIN_SAMPLES} samples)"
        )

    return {
        "match_id":     match_id,
        "outcome":      actual_outcome,
        "adjusted":     len(adjustments),
        "clv_active":   clv_signal_active_any,
        "clv_value":    clv_value,
        "clv_bet_side": clv_bet_side,
        "models":       adjustments,
    }


async def run_bulk_weight_adjustment(
    db: AsyncSession,
    orchestrator: Any,
    days_back: int = 7,
) -> Dict[str, Any]:
    """
    Bulk re-run weight adjustment for all recently settled matches
    that have an audit record. Useful for initial calibration or
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
        "days_back":             days_back,
        "matches_processed":     len(settled_matches),
        "total_weight_updates":  total_adjusted,
        "summary":               summary,
    }


async def get_model_performance_report(db: AsyncSession) -> List[Dict]:
    """Return a ranked performance report for all registered models.

    For each model the response now includes:
    - ``metric_source``: ``"live"`` when ≥ BOOTSTRAP_LIVE_THRESHOLD settled
      predictions back the numbers, ``"bootstrapped"`` when the values came
      from the admin bootstrap action (type-prior or training pkl), or
      ``None`` when no metrics exist yet.
    - ``training_metrics``: accuracy / brier / log_loss extracted from the
      latest promoted version_history entry (None if not available).
    """
    result = await db.execute(
        select(ModelMetadata).order_by(ModelMetadata.weight.desc())
    )
    rows = result.scalars().all()

    report = []
    for r in rows:
        total   = r.predictions_total or 0
        correct = r.predictions_correct or 0

        # Derive metric_source
        has_metrics = r.accuracy_1x2 is not None or r.brier_score is not None
        if total >= BOOTSTRAP_LIVE_THRESHOLD:
            metric_source = "live"
        elif has_metrics:
            metric_source = "bootstrapped"
        else:
            metric_source = None

        # Pull training metrics from version_history (latest promoted entry)
        training_metrics: Optional[Dict] = None
        history = list(r.version_history or [])
        if history:
            # Prefer the promoted entry; fall back to the most recent upload
            promoted = next(
                (h for h in reversed(history) if h.get("promoted_at")), None
            ) or history[-1]
            m = promoted.get("metrics") or {}
            if m:
                training_metrics = {
                    "accuracy":      m.get("accuracy"),
                    "brier_score":   m.get("brier_score"),
                    "log_loss":      m.get("log_loss"),
                    "training_samples": promoted.get("training_samples", 0),
                    "version":       promoted.get("version"),
                }

        report.append({
            "key":                          r.key,
            "name":                         r.name,
            "model_type":                   r.model_type,
            "weight":                       r.weight,
            "accuracy_1x2":                 r.accuracy_1x2,
            "brier_score":                  r.brier_score,
            "log_loss":                     r.log_loss,
            "clv_score":                    r.clv_score,
            "clv_samples":                  r.clv_samples or 0,
            "clv_negative_streak_days":     getattr(r, "clv_negative_streak_days", 0) or 0,
            "last_clv_check_at":            r.last_clv_check_at.isoformat() if getattr(r, "last_clv_check_at", None) else None,
            "auto_demoted":                 bool(getattr(r, "auto_demoted", False)),
            "predictions_total":            total,
            "predictions_correct":          correct,
            "win_rate":                     round(correct / total, 4) if total else None,
            "pkl_loaded":                   r.pkl_loaded,
            "is_active":                    r.is_active,
            "metric_source":                metric_source,
            "training_metrics":             training_metrics,
        })
    return report


async def bootstrap_model_priors(
    db: AsyncSession,
    force: bool = False,
) -> Dict:
    """
    Seed ``brier_score``, ``log_loss``, and ``accuracy_1x2`` for models that
    have fewer than BOOTSTRAP_LIVE_THRESHOLD settled predictions.

    Priority for each model:
      1. Training metrics from the latest promoted version in ``version_history``
      2. Model-type benchmark priors from ``_TYPE_PRIORS``

    If ``force=True``, overwrites even models that already have bootstrapped
    values (useful for a manual admin reset).  Models with ≥
    BOOTSTRAP_LIVE_THRESHOLD live predictions are never overwritten.

    Returns a summary dict describing what was done.
    """
    result = await db.execute(select(ModelMetadata))
    rows = result.scalars().all()

    seeded: List[str] = []
    skipped_live: List[str] = []
    skipped_existing: List[str] = []

    for row in rows:
        total = row.predictions_total or 0

        # Never touch models with enough live data
        if total >= BOOTSTRAP_LIVE_THRESHOLD:
            skipped_live.append(row.key)
            continue

        # Skip if already has values and not forcing
        already_set = row.brier_score is not None and row.log_loss is not None
        if already_set and not force:
            skipped_existing.append(row.key)
            continue

        # Priority 1: training metrics from version_history
        history = list(row.version_history or [])
        priors: Dict[str, Any] = {}
        if history:
            promoted = next(
                (h for h in reversed(history) if h.get("promoted_at")), None
            ) or history[-1]
            m = promoted.get("metrics") or {}
            if m.get("brier_score") is not None:
                priors["brier"] = float(m["brier_score"])
            if m.get("log_loss") is not None:
                priors["log_loss"] = float(m["log_loss"])
            if m.get("accuracy") is not None:
                priors["accuracy"] = float(m["accuracy"])

        # Priority 2: type-benchmark priors for any missing fields
        type_prior = _get_type_prior(row.model_type or "")
        priors.setdefault("brier",    type_prior["brier"])
        priors.setdefault("log_loss", type_prior["log_loss"])
        priors.setdefault("accuracy", type_prior["accuracy"])

        row.brier_score  = round(priors["brier"],    5)
        row.log_loss     = round(priors["log_loss"],  5)
        # Only seed accuracy_1x2 if no live predictions have been recorded
        if total == 0:
            row.accuracy_1x2 = round(priors["accuracy"], 4)

        seeded.append(row.key)

    await db.commit()
    return {
        "seeded":           seeded,
        "seeded_count":     len(seeded),
        "skipped_live":     skipped_live,
        "skipped_existing": skipped_existing,
    }


async def reactivate_zero_sample_models(db: AsyncSession) -> Dict:
    """
    Reactivate every model that is ``is_active=False`` but has **zero** settled
    predictions.  A model with no prediction history has no empirical basis for
    demotion; this is the most common cold-start situation.

    Clears ``auto_demoted`` and ``clv_negative_streak_days`` so the streak
    monitor doesn't immediately re-demote them on the next tick.

    Returns a summary dict.
    """
    result = await db.execute(
        select(ModelMetadata).where(ModelMetadata.is_active.is_(False))
    )
    rows = result.scalars().all()

    reactivated: List[str] = []
    kept_demoted: List[str] = []

    for row in rows:
        total = row.predictions_total or 0
        if total == 0:
            row.is_active               = True
            row.auto_demoted            = False
            row.clv_negative_streak_days = 0
            reactivated.append(row.key)
        else:
            kept_demoted.append(row.key)

    await db.commit()
    return {
        "reactivated":       reactivated,
        "reactivated_count": len(reactivated),
        "kept_demoted":      kept_demoted,
    }
