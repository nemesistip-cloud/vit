"""app/ml/calibration/temperature_scaling.py — Temperature Scaling Calibrator.

Temperature scaling is a single-parameter post-hoc calibration method.
It divides logits by a scalar T (temperature) before softmax, producing
better-calibrated probabilities without changing accuracy.

T > 1 → softer (more uncertain) probabilities
T < 1 → sharper (more confident) probabilities
T = 1 → identity (no change)

Usage:
    scaler = TemperatureScaler()
    cal_probs = scaler.calibrate(home_prob, draw_prob, away_prob)
    scaler.fit(predictions_list)  # fit T from validation set
"""
from __future__ import annotations

import json
import logging
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_SAVE_PATH = Path("models") / "temperature_T.json"
_MIN_T = 0.5
_MAX_T = 3.0
_DEFAULT_T = 1.0


def _softmax(logits: List[float]) -> List[float]:
    m = max(logits)
    exps = [math.exp(l - m) for l in logits]
    s = sum(exps)
    return [e / s for e in exps]


def _probs_to_logits(probs: List[float]) -> List[float]:
    """Convert probabilities back to log-scale (pseudo-logits via log)."""
    eps = 1e-7
    return [math.log(max(p, eps)) for p in probs]


def _brier_score(pred_probs: List[Tuple[float, float, float]], actual_outcomes: List[int]) -> float:
    """
    Brier score for 1x2 predictions.
    actual_outcome: 0=home, 1=draw, 2=away
    """
    total = 0.0
    for (hp, dp, ap), outcome in zip(pred_probs, actual_outcomes):
        probs = [hp, dp, ap]
        for i, p in enumerate(probs):
            total += (p - (1.0 if i == outcome else 0.0)) ** 2
    return total / (3 * len(pred_probs)) if pred_probs else 0.0


class TemperatureScaler:
    """
    Post-hoc temperature scaling calibration for 1x2 football predictions.

    Fits a single scalar T that minimises Brier score on validation predictions.
    """

    def __init__(self, T: float = _DEFAULT_T):
        self.T = max(_MIN_T, min(_MAX_T, T))
        self._load()

    def _load(self) -> None:
        """Load persisted temperature from disk if available."""
        try:
            if _SAVE_PATH.exists():
                data = json.loads(_SAVE_PATH.read_text())
                self.T = max(_MIN_T, min(_MAX_T, float(data.get("T", _DEFAULT_T))))
                logger.info("[temp-scaler] loaded T=%.3f from %s", self.T, _SAVE_PATH)
        except Exception as exc:
            logger.debug("[temp-scaler] load failed: %s", exc)

    def save(self) -> None:
        """Persist temperature to disk."""
        try:
            _SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _SAVE_PATH.write_text(json.dumps({"T": self.T, "version": "v1"}))
            logger.info("[temp-scaler] saved T=%.3f to %s", self.T, _SAVE_PATH)
        except Exception as exc:
            logger.warning("[temp-scaler] save failed: %s", exc)

    def calibrate(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
    ) -> Tuple[float, float, float]:
        """
        Apply temperature scaling to a 1x2 probability distribution.
        Returns (home_prob_cal, draw_prob_cal, away_prob_cal) that sum to 1.0.
        """
        if self.T == 1.0:
            return home_prob, draw_prob, away_prob

        logits = _probs_to_logits([home_prob, draw_prob, away_prob])
        scaled = [l / self.T for l in logits]
        cal = _softmax(scaled)
        return round(cal[0], 4), round(cal[1], 4), round(cal[2], 4)

    def fit(
        self,
        predictions: List[Dict],
        n_iterations: int = 100,
    ) -> float:
        """
        Fit temperature T from a list of settled predictions.

        Each prediction dict must have:
            home_prob, draw_prob, away_prob, actual_outcome (0=home,1=draw,2=away)

        Returns the fitted T value.
        """
        if len(predictions) < 10:
            logger.info("[temp-scaler] fit skipped: only %d predictions (need ≥10)", len(predictions))
            return self.T

        probs = [
            (float(p["home_prob"]), float(p["draw_prob"]), float(p["away_prob"]))
            for p in predictions
        ]
        outcomes = [int(p["actual_outcome"]) for p in predictions]

        best_T = self.T
        best_brier = float("inf")

        # Grid search over temperature range
        for i in range(n_iterations):
            T_candidate = _MIN_T + (i / (n_iterations - 1)) * (_MAX_T - _MIN_T)
            cal_probs = []
            for hp, dp, ap in probs:
                logits = _probs_to_logits([hp, dp, ap])
                scaled = [l / T_candidate for l in logits]
                cal = _softmax(scaled)
                cal_probs.append(tuple(cal))

            brier = _brier_score(cal_probs, outcomes)
            if brier < best_brier:
                best_brier = brier
                best_T = T_candidate

        self.T = max(_MIN_T, min(_MAX_T, round(best_T, 3)))
        self.save()
        logger.info("[temp-scaler] fit complete: T=%.3f, Brier=%.4f (n=%d)", self.T, best_brier, len(predictions))
        return self.T


# Singleton
_scaler: Optional[TemperatureScaler] = None


def get_temperature_scaler() -> TemperatureScaler:
    global _scaler
    if _scaler is None:
        _scaler = TemperatureScaler()
    return _scaler
