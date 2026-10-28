"""
Prediction Evaluation Service — Wave 2 Prediction Intelligence Infrastructure.

Evaluates stored predictions against verified event results and produces
trustworthy, model-versioned analytics including multi-class Brier score,
log loss, accuracy by competition/sport, confidence bucket calibration,
and sample size attribution.
"""

import math
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Match, Prediction
from app.modules.sports.models import ResultVerification, ResultObservation

logger = logging.getLogger(__name__)


def compute_multiclass_brier(
    home_prob: float, draw_prob: float, away_prob: float, actual_outcome: str
) -> float:
    """
    Compute multi-class Brier score (mean squared error over 3 outcome classes).
    Lower is better (0.0 = perfect, 2.0 = worst).
    """
    target_home = 1.0 if actual_outcome == "home" else 0.0
    target_draw = 1.0 if actual_outcome == "draw" else 0.0
    target_away = 1.0 if actual_outcome == "away" else 0.0

    sq_err = (
        (home_prob - target_home) ** 2 +
        (draw_prob - target_draw) ** 2 +
        (away_prob - target_away) ** 2
    )
    return sq_err / 3.0


def compute_log_loss(
    home_prob: float, draw_prob: float, away_prob: float, actual_outcome: str
) -> float:
    """Compute cross-entropy log loss clipped to [1e-15, 1 - 1e-15]."""
    eps = 1e-15
    if actual_outcome == "home":
        p = max(eps, min(1.0 - eps, home_prob))
    elif actual_outcome == "draw":
        p = max(eps, min(1.0 - eps, draw_prob))
    elif actual_outcome == "away":
        p = max(eps, min(1.0 - eps, away_prob))
    else:
        return 0.0
    return -math.log(p)


class PredictionEvaluationService:
    @staticmethod
    async def evaluate_match_predictions(
        db: AsyncSession,
        match_id: int
    ) -> Dict[str, Any]:
        """
        Evaluate all predictions for a match using ONLY verified event results.
        Enforces temporal integrity (predictions created before kickoff/result).
        """
        # Fetch verified result
        v_stmt = select(ResultVerification).where(ResultVerification.match_id == match_id)
        v_res = await db.execute(v_stmt)
        verification = v_res.scalar_one_or_none()

        if not verification or verification.verification_status != "VERIFIED":
            return {
                "match_id": match_id,
                "status": "SKIPPED",
                "reason": f"Match ID {match_id} result is not VERIFIED (status: {verification.verification_status if verification else 'NO_RECORD'})",
                "evaluated_count": 0,
            }

        actual_outcome = (verification.verified_outcome or "").lower()
        if actual_outcome not in {"home", "draw", "away"}:
            return {
                "match_id": match_id,
                "status": "SKIPPED",
                "reason": "Verified outcome is missing or invalid",
                "evaluated_count": 0,
            }

        # Fetch match info for kickoff time
        m_stmt = select(Match).where(Match.id == match_id)
        m_res = await db.execute(m_stmt)
        match = m_res.scalar_one_or_none()
        if not match:
            return {"match_id": match_id, "status": "ERROR", "reason": "Match record not found", "evaluated_count": 0}

        if match.source in ("seed_demo", "demo", "synthetic", "live_generated") or match.market_type == "demo":
            logger.info("Skipping demo/synthetic match %s from prediction evaluation", match_id)
            return {
                "match_id": match_id,
                "status": "SKIPPED",
                "reason": "Demo or synthetic matches are excluded from prediction evaluation.",
                "evaluated_count": 0,
            }

        # Fetch predictions for match
        p_stmt = select(Prediction).where(Prediction.match_id == match_id)
        p_res = await db.execute(p_stmt)
        predictions = p_res.scalars().all()

        evaluated_count = 0
        skipped_temporal = 0

        for pred in predictions:
            # Temporal integrity check: prediction created before kickoff
            pred_created_at = getattr(pred, "timestamp", None) or getattr(pred, "created_at", None)
            if match.kickoff_time and pred_created_at:
                pred_time = pred_created_at.replace(tzinfo=None)
                kickoff_time = match.kickoff_time.replace(tzinfo=None)
                if pred_time >= kickoff_time:
                    logger.warning(
                        "Skipping evaluation for prediction %s created post-kickoff (%s >= %s)",
                        pred.id, pred_time, kickoff_time
                    )
                    skipped_temporal += 1
                    continue

            # Evaluate the 1X2 forecast, not an optional market selection such as over/under.
            probs = {"home": pred.home_prob, "draw": pred.draw_prob, "away": pred.away_prob}
            predicted_side = max(probs, key=probs.get)

            was_correct = (predicted_side == actual_outcome)
            pred.was_correct = was_correct

            # Multi-class Brier score & log loss
            brier = compute_multiclass_brier(pred.home_prob, pred.draw_prob, pred.away_prob, actual_outcome)
            ll = compute_log_loss(pred.home_prob, pred.draw_prob, pred.away_prob, actual_outcome)

            # Record in model_consensus or extra metadata dict if present
            if pred.model_consensus is None:
                pred.model_consensus = {}
            if isinstance(pred.model_consensus, dict):
                consensus_data = dict(pred.model_consensus)
                consensus_data.update({
                    "evaluation": {
                        "verified_outcome": actual_outcome,
                        "brier_score": round(brier, 4),
                        "log_loss": round(ll, 4),
                        "evaluated_at": datetime.now(timezone.utc).isoformat(),
                    }
                })
                pred.model_consensus = consensus_data

            evaluated_count += 1

        await db.flush()
        return {
            "match_id": match_id,
            "status": "EVALUATED",
            "verified_outcome": actual_outcome,
            "evaluated_count": evaluated_count,
            "skipped_temporal_count": skipped_temporal,
        }

    @staticmethod
    async def get_performance_analytics(
        db: AsyncSession,
        sport: Optional[str] = None,
        league: Optional[str] = None,
        model_name: Optional[str] = None,
        exclude_demo: bool = True,
        time_window_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Aggregate trustworthy prediction performance analytics over verified results.
        Returns accuracy, Brier score, log loss, calibration, and sample sizes.
        """
        query = (
            select(Prediction, Match, ResultVerification)
            .join(Match, Prediction.match_id == Match.id)
            .join(ResultVerification, Match.id == ResultVerification.match_id)
            .where(
                ResultVerification.verification_status == "VERIFIED",
                func.lower(ResultVerification.verified_outcome).in_(("home", "draw", "away")),
                Prediction.was_correct.isnot(None),
            )
        )

        if exclude_demo:
            query = query.where(
                or_(
                    Match.source.is_(None),
                    Match.source.notin_(["seed_demo", "demo", "synthetic", "live_generated"]),
                ),
                or_(Match.market_type.is_(None), Match.market_type != "demo"),
                Prediction.is_seed.is_(False),
            )

        if sport and sport.lower() != "all":
            query = query.where(Match.sport == sport)

        if league and league.lower() != "all":
            query = query.where(Match.league == league)

        if time_window_days and time_window_days > 0:
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
            from datetime import timedelta
            cutoff_dt = cutoff - timedelta(days=time_window_days)
            query = query.where(Match.kickoff_time >= cutoff_dt)

        res = await db.execute(query)
        rows = res.all()

        total_predictions = len(rows)
        if total_predictions == 0:
            return {
                "sample_size": 0,
                "evaluation_window_days": time_window_days,
                "overall_accuracy": None,
                "mean_brier_score": None,
                "mean_log_loss": None,
                "confidence_calibration": [],
                "by_competition": {},
                "disclaimer": "No evaluated verified predictions found for the specified criteria.",
            }

        correct_count = 0
        total_brier = 0.0
        total_log_loss = 0.0

        by_comp: Dict[str, Dict[str, Any]] = {}
        conf_buckets: Dict[str, Dict[str, Any]] = {
            "0.0-0.4": {"correct": 0, "total": 0, "prob_sum": 0.0},
            "0.4-0.6": {"correct": 0, "total": 0, "prob_sum": 0.0},
            "0.6-0.8": {"correct": 0, "total": 0, "prob_sum": 0.0},
            "0.8-1.0": {"correct": 0, "total": 0, "prob_sum": 0.0},
        }

        for pred, match, ver in rows:
            if pred.was_correct:
                correct_count += 1

            actual = (ver.verified_outcome or "").lower()
            bri = compute_multiclass_brier(pred.home_prob, pred.draw_prob, pred.away_prob, actual)
            ll = compute_log_loss(pred.home_prob, pred.draw_prob, pred.away_prob, actual)

            total_brier += bri
            total_log_loss += ll

            # Competition breakdown
            comp = match.league or "Unknown"
            if comp not in by_comp:
                by_comp[comp] = {"correct": 0, "total": 0, "brier_sum": 0.0}
            by_comp[comp]["total"] += 1
            if pred.was_correct:
                by_comp[comp]["correct"] += 1
            by_comp[comp]["brier_sum"] += bri

            # Confidence bucket calibration
            max_p = max(pred.home_prob, pred.draw_prob, pred.away_prob)
            if max_p < 0.4:
                b_key = "0.0-0.4"
            elif max_p < 0.6:
                b_key = "0.4-0.6"
            elif max_p < 0.8:
                b_key = "0.6-0.8"
            else:
                b_key = "0.8-1.0"

            conf_buckets[b_key]["total"] += 1
            conf_buckets[b_key]["prob_sum"] += max_p
            if pred.was_correct:
                conf_buckets[b_key]["correct"] += 1

        acc = round(correct_count / float(total_predictions), 4)
        mean_brier = round(total_brier / float(total_predictions), 4)
        mean_ll = round(total_log_loss / float(total_predictions), 4)

        # Process comp stats
        comp_summary = {}
        for c, data in by_comp.items():
            cnt = data["total"]
            comp_summary[c] = {
                "sample_size": cnt,
                "accuracy": round(data["correct"] / float(cnt), 4) if cnt > 0 else None,
                "mean_brier": round(data["brier_sum"] / float(cnt), 4) if cnt > 0 else None,
            }

        # Process calibration
        calibration_list = []
        for b_name, b_data in conf_buckets.items():
            cnt = b_data["total"]
            calibration_list.append({
                "bucket": b_name,
                "sample_size": cnt,
                "avg_predicted_confidence": round(b_data["prob_sum"] / float(cnt), 4) if cnt > 0 else None,
                "observed_accuracy": round(b_data["correct"] / float(cnt), 4) if cnt > 0 else None,
            })

        return {
            "sample_size": total_predictions,
            "evaluation_window_days": time_window_days,
            "overall_accuracy": acc,
            "mean_brier_score": mean_brier,
            "mean_log_loss": mean_ll,
            "confidence_calibration": calibration_list,
            "by_competition": comp_summary,
            "disclaimer": "Historical accuracy performance is informational and does not guarantee future results.",
        }
