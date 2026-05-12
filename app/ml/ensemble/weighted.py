"""app/ml/ensemble/weighted.py — Brier-Weighted Ensemble.

Tracks per-model Brier score from settled predictions and updates
ensemble weights so better-calibrated models get more influence.

weight_i = 1 / (brier_i + epsilon)
weights normalised to sum to 1.0

Usage:
    ensemble = BrierWeightedEnsemble()
    await ensemble.update_weights(db)
    weights = ensemble.get_weights()
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_WEIGHTS_PATH = Path("models") / "brier_weights.json"
_EPSILON      = 0.01   # prevents division by zero; caps max weight at 1/ε = 100
_MIN_SAMPLES  = 5      # minimum settled predictions before updating weight


def _brier_score_one(pred_probs: List[float], actual_idx: int) -> float:
    """Single-prediction Brier score component for one model."""
    return sum((p - (1.0 if i == actual_idx else 0.0)) ** 2 for i, p in enumerate(pred_probs))


class BrierWeightedEnsemble:
    """
    Maintains a per-model weight dictionary derived from historical Brier scores.
    Falls back to uniform weights if no data is available.
    """

    # Default model weights (used before any data is collected)
    DEFAULT_WEIGHTS: Dict[str, float] = {
        "xgb_v2":         0.12,
        "lstm_v2":        0.09,
        "poisson_v2":     0.08,
        "hybrid_v2":      0.08,
        "transformer_v2": 0.08,
        "ensemble_v2":    0.07,
        "dixon_coles_v2": 0.07,
        "bayes_v2":       0.06,
        "market_v2":      0.10,
        "rf_v2":          0.05,
        "logistic_v2":    0.06,
        "elo_v2":         0.04,
        "llm_consensus_v2": 0.10,
    }

    def __init__(self) -> None:
        self._weights: Dict[str, float] = dict(self.DEFAULT_WEIGHTS)
        self._brier_scores: Dict[str, float] = {}
        self._sample_counts: Dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        try:
            if _WEIGHTS_PATH.exists():
                data = json.loads(_WEIGHTS_PATH.read_text())
                if "weights" in data:
                    self._weights = data["weights"]
                if "brier_scores" in data:
                    self._brier_scores = data["brier_scores"]
                if "sample_counts" in data:
                    self._sample_counts = data["sample_counts"]
                logger.info("[brier-ensemble] loaded weights for %d models", len(self._weights))
        except Exception as exc:
            logger.debug("[brier-ensemble] load failed: %s", exc)

    def save(self) -> None:
        try:
            _WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            _WEIGHTS_PATH.write_text(json.dumps({
                "weights":       self._weights,
                "brier_scores":  self._brier_scores,
                "sample_counts": self._sample_counts,
            }, indent=2))
        except Exception as exc:
            logger.warning("[brier-ensemble] save failed: %s", exc)

    def get_weights(self) -> Dict[str, float]:
        """Return current normalised weights dict."""
        return dict(self._weights)

    def record_prediction(
        self,
        model_name: str,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        actual_outcome: int,  # 0=home, 1=draw, 2=away
    ) -> None:
        """Record a settled prediction for a model (running average Brier update)."""
        bs = _brier_score_one([home_prob, draw_prob, away_prob], actual_outcome)
        n = self._sample_counts.get(model_name, 0)
        old_brier = self._brier_scores.get(model_name, bs)
        # Exponential moving average: α=0.1 → slow drift
        new_brier = 0.9 * old_brier + 0.1 * bs if n > 0 else bs
        self._brier_scores[model_name] = round(new_brier, 5)
        self._sample_counts[model_name] = n + 1

    def recompute_weights(self) -> None:
        """
        Recompute ensemble weights from accumulated Brier scores.
        Only updates models that have enough samples.
        """
        raw: Dict[str, float] = {}
        for model, brier in self._brier_scores.items():
            n = self._sample_counts.get(model, 0)
            if n >= _MIN_SAMPLES:
                raw[model] = 1.0 / (brier + _EPSILON)
            else:
                # Keep default weight until enough data
                raw[model] = self._weights.get(model, 1.0 / (0.33 + _EPSILON))

        total = sum(raw.values())
        if total > 0:
            self._weights = {m: round(w / total, 6) for m, w in raw.items()}

        self.save()
        logger.info(
            "[brier-ensemble] recomputed weights: %d models, top=%s",
            len(self._weights),
            max(self._weights, key=self._weights.get) if self._weights else "none",
        )

    async def update_weights(self, db) -> int:
        """
        Pull settled predictions from DB, record Brier scores, recompute weights.
        Returns number of predictions processed.
        """
        try:
            from app.db.models import Prediction, Match
            from sqlalchemy import select, and_

            stmt = (
                select(Prediction, Match)
                .join(Match, Match.id == Prediction.match_id)
                .where(
                    Prediction.was_correct.isnot(None),
                    Prediction.home_prob.isnot(None),
                    Prediction.model_insights.isnot(None),
                )
            )
            rows = list((await db.execute(stmt)).all())

            processed = 0
            for pred, match in rows:
                if match.actual_outcome not in ("home", "draw", "away"):
                    continue
                actual_idx = {"home": 0, "draw": 1, "away": 2}[match.actual_outcome]

                insights = pred.model_insights or []
                for ins in insights:
                    model_name = ins.get("model_name")
                    if not model_name:
                        continue
                    hp = float(ins.get("home_prob") or pred.home_prob or 0.33)
                    dp = float(ins.get("draw_prob") or pred.draw_prob or 0.33)
                    ap = float(ins.get("away_prob") or pred.away_prob or 0.34)
                    self.record_prediction(model_name, hp, dp, ap, actual_idx)
                processed += 1

            if processed > 0:
                self.recompute_weights()
            return processed

        except Exception as exc:
            logger.error("[brier-ensemble] update_weights error: %s", exc)
            return 0

    def blend(self, model_outputs: List[Dict]) -> Dict[str, float]:
        """
        Blend multiple model outputs using Brier-weighted averaging.

        Each dict in model_outputs should have:
            model_name, home_prob, draw_prob, away_prob

        Returns blended {home_prob, draw_prob, away_prob}.
        """
        if not model_outputs:
            return {"home_prob": 0.45, "draw_prob": 0.27, "away_prob": 0.28}

        total_w = 0.0
        h_sum = d_sum = a_sum = 0.0

        for out in model_outputs:
            name = out.get("model_name", "unknown")
            w = self._weights.get(name, 1.0 / max(len(model_outputs), 1))
            hp = float(out.get("home_prob") or 0.0)
            dp = float(out.get("draw_prob") or 0.0)
            ap = float(out.get("away_prob") or 0.0)
            s = hp + dp + ap
            if s <= 0:
                continue
            # Normalise individual model output
            hp, dp, ap = hp / s, dp / s, ap / s
            h_sum += w * hp
            d_sum += w * dp
            a_sum += w * ap
            total_w += w

        if total_w <= 0:
            return {"home_prob": 0.45, "draw_prob": 0.27, "away_prob": 0.28}

        s = h_sum + d_sum + a_sum
        return {
            "home_prob": round(h_sum / s, 4),
            "draw_prob": round(d_sum / s, 4),
            "away_prob": round(a_sum / s, 4),
        }


# Singleton
_ensemble: Optional[BrierWeightedEnsemble] = None


def get_brier_ensemble() -> BrierWeightedEnsemble:
    global _ensemble
    if _ensemble is None:
        _ensemble = BrierWeightedEnsemble()
    return _ensemble
