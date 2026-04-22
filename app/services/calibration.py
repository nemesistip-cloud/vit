"""
Probability calibration registry for the 12-model ensemble (Phase C).

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
from typing import Dict, List, Optional, Tuple

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
    if s <= 0:
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

    # ------------------------------------------------------------------ load
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
                "CALIBRATION no fitted calibrators found in %s — "
                "predictions will be uncalibrated. Run "
                "POST /admin/calibration/fit (or python -m scripts.fit_calibrators) "
                "after enough settled predictions accumulate.",
                self.root,
            )

    # --------------------------------------------------------------- inspect
    def has_calibrator(self, model_name: str, method: str = DEFAULT_METHOD) -> bool:
        m = self._store.get(model_name, {})
        return all(method in m.get(k, {}) for k in CLASSES)

    def coverage(self, method: str = DEFAULT_METHOD) -> Dict[str, bool]:
        return {name: self.has_calibrator(name, method) for name in self._store}

    # ------------------------------------------------------------------ apply
    def apply(
        self,
        model_name: str,
        hp: float,
        dp: float,
        ap: float,
        method: str = DEFAULT_METHOD,
    ) -> Tuple[Tuple[float, float, float], Dict[str, object]]:
        """
        Returns ((hp_cal, dp_cal, ap_cal), meta).
        meta = {applied: bool, method: str, partial: bool, missing_classes: [...]}
        """
        meta: Dict[str, object] = {
            "applied": False,
            "method": method,
            "partial": False,
            "missing_classes": [],
        }
        if method not in SUPPORTED_METHODS:
            meta["error"] = f"unsupported method {method!r}"
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
            except Exception as e:
                logger.warning(
                    "CALIBRATION apply failed model=%s class=%s method=%s: %s",
                    model_name, klass, method, e,
                )
                meta["missing_classes"].append(klass)

        if applied_any:
            hp2, dp2, ap2 = _normalise(out["home"], out["draw"], out["away"])
            meta["applied"] = True
            meta["partial"] = bool(meta["missing_classes"])
            return (hp2, dp2, ap2), meta

        return (hp, dp, ap), meta


# ============================================================================
# Fitting from settled prediction history
# ============================================================================

async def fit_from_history(
    db,
    method: str = "both",
    min_samples: int = 50,
) -> Dict[str, object]:
    """
    Fit Platt + Isotonic calibrators per (model, class) from settled predictions.

    Mines `Prediction.model_insights` (JSON list of per-model rows) joined to
    `Match.actual_outcome`. Persists fitted estimators under CALIBRATORS_DIR.

    Returns a structured report:
      {
        "n_settled_matches": int,
        "models_fitted": {model_name: {"samples": n, "methods": [...]}},
        "models_skipped": {model_name: reason},
      }
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload  # noqa: F401

    from app.db.models import Match, Prediction
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression

    if method not in ("platt", "isotonic", "both"):
        raise ValueError(f"method must be platt|isotonic|both, got {method!r}")
    methods = ("platt", "isotonic") if method == "both" else (method,)

    q = (
        select(Prediction, Match)
        .join(Match, Match.id == Prediction.match_id)
        .where(Match.actual_outcome.isnot(None))
        .where(Prediction.model_insights.isnot(None))
    )
    rows = (await db.execute(q)).all()
    n_settled = len(rows)

    # Collect per (model, class) samples
    samples: Dict[str, Dict[str, List[Tuple[float, int]]]] = {}
    for pred, match in rows:
        actual = (match.actual_outcome or "").lower()
        if actual not in CLASSES:
            continue
        insights = pred.model_insights or []
        if not isinstance(insights, list):
            continue
        for row in insights:
            name = row.get("model_name")
            if not name:
                continue
            for klass in CLASSES:
                key = f"{klass}_prob"
                p = row.get(key)
                if p is None:
                    continue
                try:
                    p = float(p)
                except Exception:
                    continue
                y = 1 if klass == actual else 0
                samples.setdefault(name, {}).setdefault(klass, []).append((p, y))

    report: Dict[str, object] = {
        "n_settled_matches": n_settled,
        "min_samples": min_samples,
        "models_fitted": {},
        "models_skipped": {},
    }

    CALIBRATORS_DIR.mkdir(parents=True, exist_ok=True)

    for name, by_class in samples.items():
        n = min(len(by_class.get(k, [])) for k in CLASSES) if all(k in by_class for k in CLASSES) else 0
        if n < min_samples:
            report["models_skipped"][name] = f"insufficient samples (have {n}, need {min_samples})"
            continue

        fitted_methods: List[str] = []
        # Need both classes present (positive AND negative) per class to fit
        for klass in CLASSES:
            data = by_class[klass]
            xs = np.array([d[0] for d in data]).reshape(-1, 1)
            ys = np.array([d[1] for d in data])
            if ys.sum() == 0 or ys.sum() == len(ys):
                logger.warning(
                    "CALIBRATION fit skipped %s/%s — degenerate labels (all %d)",
                    name, klass, int(ys[0]),
                )
                continue
            for m in methods:
                try:
                    if m == "platt":
                        est = LogisticRegression(C=1.0, solver="lbfgs", max_iter=200)
                        est.fit(xs, ys)
                    else:  # isotonic
                        est = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
                        est.fit(xs.ravel(), ys.astype(float))
                    out_path = CALIBRATORS_DIR / f"{name}_{klass}_{m}.pkl"
                    joblib.dump(est, out_path)
                    if m not in fitted_methods:
                        fitted_methods.append(m)
                except Exception as e:
                    logger.exception("CALIBRATION fit failed %s/%s/%s: %s",
                                     name, klass, m, e)

        report["models_fitted"][name] = {
            "samples_per_class": {k: len(by_class[k]) for k in CLASSES},
            "methods": fitted_methods,
        }

    # Hot-reload registry so new calibrators apply immediately
    CalibratorRegistry.reload()
    logger.info(
        "CALIBRATION fit complete: %d models fitted, %d skipped, from %d settled matches",
        len(report["models_fitted"]), len(report["models_skipped"]), n_settled,
    )
    return report
