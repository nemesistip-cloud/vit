"""
Probability calibration registry for the 13-model ensemble (Phase C).

Provides per-model, per-class (home/draw/away) calibrators trained on
historical (predicted_prob, actual_outcome) pairs.

Two methods are supported:
  * platt    — sklearn LogisticRegression on the raw probability
  * isotonic — sklearn IsotonicRegression (non-parametric, monotonic)

Calibrators are persisted as joblib pickles under models/calibrators/:
    {model_name}_{class}_{method}.pkl     e.g. xgb_home_isotonic.pkl

Apply contract: calibrate_one_model(model_name, hp, dp, ap, method) -> (hp, dp, ap)
If any of the three class calibrators is missing, that class falls through
identity and the meta returned by `last_apply_meta()` records the gap so
the predict route can surface it via `data_quality.calibration`.

The registry is cached at process scope; call `reload()` after retraining
to pick up new pickles without restart.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import joblib
import numpy as np

logger = logging.getLogger(__name__)

CALIBRATORS_DIR = Path(os.getenv("CALIBRATORS_DIR", "models/calibrators"))
DEFAULT_METHOD = os.getenv("CALIBRATION_METHOD", "isotonic").lower()
CLASSES = ("home", "draw", "away")
SUPPORTED_METHODS = ("platt", "isotonic")


def _safe_clip(x: float) -> float:
    return float(min(0.999, max(0.001, x)))


def _normalise(h: float, d: float, a: float) -> Tuple[float, float, float]:
    s = h + d + a
    if s <= 1e-9:
        return 1 / 3, 1 / 3, 1 / 3
    return h / s, d / s, a / s


class CalibratorRegistry:
    """Process-singleton registry of fitted calibrators keyed by model_name."""

    _instance: Optional["CalibratorRegistry"] = None

    def __init__(self, root: Path = CALIBRATORS_DIR) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        # _store[model_name][class][method] = fitted estimator
        self._store: Dict[str, Dict[str, Dict[str, object]]] = {}
        self._load_all()

    @classmethod
    def get(cls) -> "CalibratorRegistry":
        if cls._instance is None:
            cls._instance = CalibratorRegistry()
        return cls._instance

    @classmethod
    def reload(cls) -> "CalibratorRegistry":
        cls._instance = CalibratorRegistry()
        return cls._instance

    def _load_all(self) -> None:
        loaded = 0
        for p in self.root.glob("*.pkl"):
            stem = p.stem  # e.g. xgb_home_isotonic
            parts = stem.rsplit("_", 2)
            if len(parts) != 3 or parts[1] not in CLASSES or parts[2] not in SUPPORTED_METHODS:
                continue
            model_name, klass, method = parts
            try:
                est = joblib.load(p)
            except Exception as e:
                logger.warning("CALIBRATION load failed for %s: %s", p.name, e)
                continue
            self._store.setdefault(model_name, {}).setdefault(klass, {})[method] = est
            loaded += 1
        if loaded:
            logger.info("CALIBRATION loaded %d calibrators across %d models",
                        loaded, len(self._store))
        else:
            logger.warning(
                "CALIBRATION no fitted calibrators found in %s — uncalibrated. Run retrain.",
                self.root,
            )

    def apply(
        self,
        model_name: str,
        hp: float,
        dp: float,
        ap: float,
        method: str = DEFAULT_METHOD,
    ) -> Tuple[Tuple[float, float, float], Dict[str, object]]:
        meta: Dict[str, object] = {
            "applied": False,
            "method": method,
            "partial": False,
            "missing_classes": [],
        }
        if method not in SUPPORTED_METHODS:
            return (hp, dp, ap), meta

        per_class = self._store.get(model_name, {})
        if not per_class:
            meta["missing_classes"] = list(CLASSES)
            return (hp, dp, ap), meta

        out = {"home": hp, "draw": dp, "away": ap}
        applied_any = False
        for klass, raw in (("home", hp), ("draw", dp), ("away", ap)):
            est = per_class.get(klass, {}).get(method)
            if est is None:
                meta["missing_classes"].append(klass)
                continue
            try:
                x = np.array([[_safe_clip(raw)]])
                if hasattr(est, "predict_proba"):
                    cal = float(est.predict_proba(x)[0, 1])
                else:  # IsotonicRegression
                    cal = float(est.predict([_safe_clip(raw)])[0])
                out[klass] = _safe_clip(cal)
                applied_any = True
            except Exception:
                meta["missing_classes"].append(klass)

        meta["applied"] = applied_any
        meta["partial"] = bool(meta["missing_classes"])
        final_probs = _normalise(out["home"], out["draw"], out["away"])
        return final_probs, meta

class CalibrationService:
    def __init__(self):
        self.predictions = []
    def record_prediction(self, home_prob, draw_prob, away_prob, actual):
        self.predictions.append({"probs": (home_prob, draw_prob, away_prob), "actual": actual})
    def calibration_report(self):
        return {"samples": len(self.predictions), "status": "recorded"}

async def fit_from_history(db: Any) -> Dict[str, Any]:
    # Original implementation is preserved here for completeness
    from sklearn.linear_model import LogisticRegression
    from sklearn.isotonic import IsotonicRegression
    from sqlalchemy import select, and_
    from app.db.models import Prediction, Match

    stmt = select(Prediction.match_id, Prediction.home_prob, Prediction.draw_prob, Prediction.away_prob, Prediction.model_insights, Match.actual_outcome).join(Match, Match.id == Prediction.match_id).where(Match.actual_outcome.in_(CLASSES))
    rows = (await db.execute(stmt)).fetchall()
    n_settled = len(rows)
    if n_settled < 100:
        return {"status": "skipped", "message": f"Too few samples ({n_settled})"}

    samples = {}
    for mid, hp, dp, ap, insights, actual in rows:
        try:
            raw_preds = json.loads(insights).get("individual_results", [])
        except Exception: continue
        for r in raw_preds:
            name = r.get("model_name")
            if not name: continue
            samples.setdefault(name, {"home": [], "draw": [], "away": []})
            for klass in CLASSES:
                val = r.get(f"{klass}_prob")
                if val is not None:
                    target = 1.0 if actual == klass else 0.0
                    samples[name][klass].append((float(val), target))

    report = {"models_fitted": {}, "models_skipped": []}
    for name, by_class in samples.items():
        fitted_methods = []
        for klass in CLASSES:
            data = by_class[klass]
            if len(data) < 30: continue
            X = np.array([d[0] for d in data]).reshape(-1, 1)
            y = np.array([d[1] for d in data])
            try:
                platt = LogisticRegression(C=1e5).fit(X, y)
                joblib.dump(platt, CALIBRATORS_DIR / f"{name}_{klass}_platt.pkl")
                iso = IsotonicRegression(out_of_bounds="clip").fit(X.ravel(), y)
                joblib.dump(iso, CALIBRATORS_DIR / f"{name}_{klass}_isotonic.pkl")
                fitted_methods.append("platt")
                fitted_methods.append("isotonic")
            except Exception: continue
        report["models_fitted"][name] = {"methods": list(set(fitted_methods))}

    CalibratorRegistry.reload()
    return report
