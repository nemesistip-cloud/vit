#!/usr/bin/env python3
"""
Fit Platt + Isotonic calibrators per (model, class) directly from the
historical CSV by replaying predictions through the trained .pkl models.

This bypasses the DB-history fitter (which requires settled Prediction
rows) and gives us hundreds of samples per model immediately.

Output: models/calibrators/{model_name}_{class}_{method}.pkl
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.ml_service.models.algorithmic import (  # noqa: F401
    PoissonModel, DixonColesModel, EloModel, BayesianNetModel,
    MarketImpliedModel, TinySequenceModel, StackedMetaModel,
)
from scripts.train_remaining_models import build_features, _odds_to_lambdas

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("fit_calibrators_csv")

MODELS_DIR = ROOT / "models"
CALIB_DIR = MODELS_DIR / "calibrators"
CLASSES = ("home", "draw", "away")  # order matches y in {0,1,2}


def load_model(name: str):
    p = MODELS_DIR / f"{name}.pkl"
    if not p.exists():
        return None
    try:
        payload = joblib.load(p)
        return payload.get("model") if isinstance(payload, dict) else payload
    except Exception as e:
        log.warning(f"  ✗ {name}: load failed ({e})")
        return None


def fit_one(probs: np.ndarray, y_bin: np.ndarray, method: str):
    if method == "platt":
        clf = LogisticRegression(C=1.0, max_iter=500, solver="lbfgs")
        clf.fit(probs.reshape(-1, 1), y_bin)
        return clf
    if method == "isotonic":
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.001, y_max=0.999)
        iso.fit(probs, y_bin)
        return iso
    raise ValueError(method)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/historical_matches.csv")
    ap.add_argument("--holdout", type=float, default=0.30,
                    help="fraction of matches reserved for calibration fitting")
    ap.add_argument("--min-samples", type=int, default=50)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    rename = {
        "HomeTeam": "home_team", "AwayTeam": "away_team",
        "FTR": "ftr", "B365H": "home_odds", "B365D": "draw_odds", "B365A": "away_odds",
    }
    df = df.rename(columns=rename)
    df["date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date", "home_team", "away_team", "ftr",
                           "home_odds", "draw_odds", "away_odds"])
    df = df.sort_values("date").reset_index(drop=True)

    # Holdout split
    n = len(df)
    cut = int(n * (1 - args.holdout))
    df_cal = df.iloc[cut:].reset_index(drop=True)
    log.info(f"Calibration set: {len(df_cal)} matches (out of {n})")

    # Build inputs for predict_1x2
    rows = []
    for _, r in df_cal.iterrows():
        ho, do_, ao = float(r["home_odds"]), float(r["draw_odds"]), float(r["away_odds"])
        # Market-implied base probabilities (de-vigged)
        inv = 1/ho + 1/do_ + 1/ao
        base_hp, base_dp, base_ap = (1/ho)/inv, (1/do_)/inv, (1/ao)/inv
        lam_h, lam_a = _odds_to_lambdas(ho, do_, ao)
        ftr = str(r["ftr"]).upper()
        y_idx = 0 if ftr == "H" else 1 if ftr == "D" else 2 if ftr == "A" else -1
        if y_idx < 0:
            continue
        rows.append({
            "base_hp": base_hp, "base_dp": base_dp, "base_ap": base_ap,
            "lam_h": lam_h, "lam_a": lam_a,
            "home_team": str(r["home_team"]), "away_team": str(r["away_team"]),
            "market_odds": {"home": ho, "draw": do_, "away": ao},
            "y": y_idx,
        })
    y_cal = np.array([r["y"] for r in rows], dtype=int)
    X_cal = rows  # keep as list of dicts
    log.info(f"Usable calibration rows: {len(rows)}")

    sklearn_models = {"gbm_v1", "lgbm_v1"}  # raw sklearn — different schema, skip
    target_models = [
        "logistic_v1", "rf_v1", "xgb_v1",
        "poisson_v1", "dixon_coles_v1", "elo_v1", "bayes_v1", "market_v1",
        "lstm_v1", "transformer_v1", "ensemble_v1", "hybrid_v1",
    ]

    CALIB_DIR.mkdir(parents=True, exist_ok=True)
    fitted, skipped = {}, {}

    for name in target_models:
        model = load_model(name)
        if model is None:
            skipped[name] = "model pkl missing"
            continue
        try:
            preds = []
            for i, row in enumerate(X_cal):
                hp, dp, ap = model.predict_1x2(
                    row["base_hp"], row["base_dp"], row["base_ap"],
                    row["lam_h"], row["lam_a"],
                    row["home_team"], row["away_team"],
                    row["market_odds"], seed=i,
                )
                preds.append((hp, dp, ap))
            proba = np.asarray(preds, dtype=float)
        except Exception as e:
            skipped[name] = f"predict_1x2 failed: {e}"
            continue
        if proba.shape != (len(X_cal), 3):
            skipped[name] = f"bad shape {proba.shape}"
            continue

        per_class = {}
        for ci, klass in enumerate(CLASSES):
            p = np.clip(proba[:, ci], 0.001, 0.999)
            y_bin = (y_cal == ci).astype(int)
            if y_bin.sum() < args.min_samples or (1 - y_bin).sum() < args.min_samples:
                per_class[klass] = "insufficient class balance"
                continue
            for method in ("platt", "isotonic"):
                est = fit_one(p, y_bin, method)
                out = CALIB_DIR / f"{name}_{klass}_{method}.pkl"
                joblib.dump(est, out)
            per_class[klass] = "ok"
        fitted[name] = {"samples": int(len(X_cal)), "per_class": per_class}
        log.info(f"  ✅ {name:18s} {per_class}")

    # Optional: also fit calibrators for the sklearn models if their feature
    # schema matches. We skip them by default because they were trained on a
    # different 10-column schema.
    for name in sklearn_models:
        skipped[name] = "10-feature schema mismatch with orchestrator runtime"

    report = {
        "n_samples": len(X_cal),
        "min_samples_per_class": args.min_samples,
        "models_fitted": fitted,
        "models_skipped": skipped,
        "output_dir": str(CALIB_DIR),
    }
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
