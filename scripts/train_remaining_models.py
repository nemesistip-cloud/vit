"""
Train the 8 non-sklearn models in the VIT ensemble:

    poisson_v1, dixon_coles_v1, elo_v1, bayes_v1,
    lstm_v1, transformer_v1, ensemble_v1, hybrid_v1, market_v1

Each produces a `.pkl` payload at /models/<key>.pkl with the same shape
expected by services/ml_service/model_loader.py:

    {
        "model":            <obj with predict_proba(X) -> ndarray (n,3)>,
        "scaler":           None or sklearn scaler,
        "feature_columns":  list[str]   # keys present in orchestrator's feature_map
        "training_samples": int,
        "class_labels":     ["home", "draw", "away"],
        "version":          "2.0.0",
        "metrics":          {"accuracy": float, "log_loss": float},
    }

Usage:
    python scripts/train_remaining_models.py --csv data/historical_matches.csv
"""
from __future__ import annotations

import argparse
import logging
import math
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.ml_service.models.algorithmic import (
    PoissonModel, DixonColesModel, EloModel, BayesianNetModel,
    MarketImpliedModel, TinySequenceModel, StackedMetaModel,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("train_remaining")

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Feature columns aligned with orchestrator's runtime feature_map
# (see services/ml_service/models/model_orchestrator.py::_sklearn_predict)
FEATURE_COLUMNS = [
    "lambda_home_est",
    "lambda_away_est",
    "elo_diff",
    "home_form_pts_5",
    "away_form_pts_5",
    "home_adv_league",
    "h2h_home_win_pct",
    "h2h_draw_pct",
    "h2h_away_win_pct",
]

CLASS_LABELS = ["home", "draw", "away"]
MAX_GOALS = 10


# ── Data prep ────────────────────────────────────────────────────────────────

def _safe_float(x, default=0.0):
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def _result_to_idx(ftr: str) -> int:
    return {"H": 0, "D": 1, "A": 2}.get(str(ftr).upper().strip(), -1)


def _odds_to_lambdas(ho: float, do_: float, ao: float) -> tuple[float, float]:
    if ho < 1.01: ho = 2.30
    if do_ < 1.01: do_ = 3.30
    if ao < 1.01: ao = 3.10
    inv = 1.0 / ho + 1.0 / do_ + 1.0 / ao
    hi, ai = (1.0 / ho) / inv, (1.0 / ao) / inv
    lam_h = max(0.3, -math.log(max(1e-9, 1.0 - hi)) * 1.5)
    lam_a = max(0.3, -math.log(max(1e-9, 1.0 - ai)) * 1.3)
    return lam_h, lam_a


def load_dataset(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="latin-1", low_memory=False)
    rename = {
        "HomeTeam": "home_team", "AwayTeam": "away_team",
        "FTHG": "fthg", "FTAG": "ftag", "FTR": "ftr",
        "B365H": "home_odds", "B365D": "draw_odds", "B365A": "away_odds",
        "PSH": "psh", "PSD": "psd", "PSA": "psa",
        "Date": "date",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    needed = {"home_team", "away_team", "ftr"}
    if not needed.issubset(df.columns):
        raise ValueError(f"CSV missing required columns: {needed - set(df.columns)}")

    df = df[df["ftr"].isin(["H", "D", "A"])].copy()

    for col in ("home_odds", "draw_odds", "away_odds"):
        df[col] = df.get(col).fillna(0).apply(_safe_float)

    # Fallback to PS odds where B365 missing
    for b, p in (("home_odds", "psh"), ("draw_odds", "psd"), ("away_odds", "psa")):
        if p in df.columns:
            df[b] = df[b].where(df[b] >= 1.01, df[p].apply(_safe_float))

    df["fthg"] = df.get("fthg", 0).fillna(0).apply(_safe_float).astype(int)
    df["ftag"] = df.get("ftag", 0).fillna(0).apply(_safe_float).astype(int)

    # Chronological order
    if "date" in df.columns:
        df["__dt"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
        df = df.sort_values("__dt").reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)

    log.info(f"Loaded {len(df)} matches from {csv_path.name}")
    return df


# ── Feature engineering (mirrors runtime feature_map) ────────────────────────

def build_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Walk the dataset chronologically, computing features that depend only on
    information available BEFORE each match (no leakage):
      - rolling form (last 5 league points)
      - Elo rating difference
      - lambda_h / lambda_a from closing odds (market view)
      - H2H last-5 percentages
      - home advantage = league-wide home win %
    """
    elo = defaultdict(lambda: 1500.0)
    K = 24.0

    last_results: dict[str, list[int]] = defaultdict(list)  # 3=W,1=D,0=L
    h2h: dict[tuple[str, str], list[str]] = defaultdict(list)  # FTR list

    n_home_wins = 0
    n_total = 0

    X, y = [], []
    for _, r in df.iterrows():
        home, away = r["home_team"], r["away_team"]
        lam_h, lam_a = _odds_to_lambdas(r["home_odds"], r["draw_odds"], r["away_odds"])
        elo_diff = elo[home] - elo[away]

        h_pts5 = sum(last_results[home][-5:]) / max(1, len(last_results[home][-5:]))
        a_pts5 = sum(last_results[away][-5:]) / max(1, len(last_results[away][-5:]))

        league_home_adv = (n_home_wins / n_total) if n_total else 0.46

        key = tuple(sorted((home, away)))
        h2h_recent = h2h[key][-5:]
        if h2h_recent:
            n = len(h2h_recent)
            # Outcomes are stored from the perspective of the original match
            # (we always remap to "home_now" perspective below)
            home_wins = draws = away_wins = 0
            for ftr, h0 in h2h_recent:
                # ftr ∈ H/D/A from when h0 was the home side
                if ftr == "D":
                    draws += 1
                elif (ftr == "H" and h0 == home) or (ftr == "A" and h0 == away):
                    home_wins += 1
                else:
                    away_wins += 1
            h2h_h = home_wins / n
            h2h_d = draws / n
            h2h_a = away_wins / n
        else:
            h2h_h, h2h_d, h2h_a = 0.45, 0.27, 0.28

        feat = [
            lam_h,
            lam_a,
            elo_diff,
            h_pts5,
            a_pts5,
            league_home_adv,
            h2h_h,
            h2h_d,
            h2h_a,
        ]

        idx = _result_to_idx(r["ftr"])
        if idx < 0:
            continue
        X.append(feat)
        y.append(idx)

        # ── Update state AFTER recording features (no leakage) ──
        # Elo update
        exp_h = 1.0 / (1.0 + 10 ** ((elo[away] - elo[home]) / 400.0))
        s_h = 1.0 if r["ftr"] == "H" else 0.5 if r["ftr"] == "D" else 0.0
        elo[home] += K * (s_h - exp_h)
        elo[away] += K * ((1.0 - s_h) - (1.0 - exp_h))

        # Form
        pts_h = 3 if r["ftr"] == "H" else 1 if r["ftr"] == "D" else 0
        pts_a = 3 if r["ftr"] == "A" else 1 if r["ftr"] == "D" else 0
        last_results[home].append(pts_h)
        last_results[away].append(pts_a)

        # H2H (store FTR + the home team at that match)
        h2h[key].append((r["ftr"], home))

        # League home advantage
        if r["ftr"] == "H":
            n_home_wins += 1
        n_total += 1

    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.int64)

    final_state = {
        "elo": dict(elo),
        "league_home_adv": (n_home_wins / n_total) if n_total else 0.46,
    }
    log.info(f"Built feature matrix: {X.shape}, classes: H={int((y==0).sum())} D={int((y==1).sum())} A={int((y==2).sum())}")
    return X, y, final_state


# ── Helpers ──────────────────────────────────────────────────────────────────

def fit_tiny_sequence_model(X: np.ndarray, y: np.ndarray) -> TinySequenceModel:
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    Xn = (X - mean) / np.where(std > 1e-6, std, 1.0)
    clf = LogisticRegression(max_iter=500, solver="lbfgs", C=1.0)
    clf.fit(Xn, y)
    return TinySequenceModel(weights=clf.coef_.T, bias=clf.intercept_,
                             mean=mean, std=std)


# ── Evaluation ───────────────────────────────────────────────────────────────

def evaluate(name: str, model, X: np.ndarray, y: np.ndarray) -> dict:
    proba = model.predict_proba(X)
    proba = np.clip(proba, 1e-6, 1.0)
    proba /= proba.sum(axis=1, keepdims=True)
    preds = proba.argmax(axis=1)
    acc = float(accuracy_score(y, preds))
    ll = float(log_loss(y, proba, labels=[0, 1, 2]))
    log.info(f"  [{name:14s}] accuracy={acc:.4f}  log_loss={ll:.4f}")
    return {"accuracy": acc, "log_loss": ll}


def save(model, key: str, samples: int, metrics: dict, version: str = "2.0.0") -> Path:
    payload = {
        "model": model,
        "scaler": None,
        "feature_columns": FEATURE_COLUMNS,
        "training_samples": samples,
        "class_labels": CLASS_LABELS,
        "version": version,
        "metrics": metrics,
    }
    out = MODELS_DIR / f"{key}.pkl"
    joblib.dump(payload, out)
    log.info(f"  [{key:14s}] ✅ saved → {out}")
    return out


# ── Orchestration ────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/historical_matches.csv")
    ap.add_argument("--holdout-frac", type=float, default=0.2,
                    help="Chronological holdout fraction for evaluation")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    df = load_dataset(csv_path)
    X, y, _state = build_features(df)
    n_total = len(X)
    n_holdout = max(1, int(n_total * args.holdout_frac))
    X_train, X_test = X[:-n_holdout], X[-n_holdout:]
    y_train, y_test = y[:-n_holdout], y[-n_holdout:]
    log.info(f"\nTrain={len(X_train)}  Holdout={len(X_test)}\n")

    log.info("Training & evaluating 8 remaining models on holdout …\n")

    # Stateless / closed-form algorithmic models — fit-free, evaluate on holdout
    poisson = PoissonModel()
    save(poisson, "poisson_v1", n_total, evaluate("poisson", poisson, X_test, y_test))

    dc = DixonColesModel(rho=-0.10)
    save(dc, "dixon_coles_v1", n_total, evaluate("dixon_coles", dc, X_test, y_test))

    elo = EloModel()
    save(elo, "elo_v1", n_total, evaluate("elo", elo, X_test, y_test))

    bayes = BayesianNetModel()
    save(bayes, "bayes_v1", n_total, evaluate("bayes", bayes, X_test, y_test))

    market = MarketImpliedModel()
    save(market, "market_v1", n_total, evaluate("market", market, X_test, y_test))

    # CPU stand-ins for the GPU sequence models — train on train split
    log.info("\nFitting CPU stand-ins for sequence models (replace with GPU later) …")
    lstm = fit_tiny_sequence_model(X_train, y_train)
    save(lstm, "lstm_v1", len(X_train), evaluate("lstm", lstm, X_test, y_test))

    trf = fit_tiny_sequence_model(X_train, y_train)
    save(trf, "transformer_v1", len(X_train), evaluate("transformer", trf, X_test, y_test))

    # Stacked meta-models — fit logistic over base-model probabilities
    log.info("\nFitting stacked meta-models …")
    base = [poisson, dc, elo, bayes, lstm, trf]
    stacked_train = np.hstack([m.predict_proba(X_train) for m in base])
    meta = LogisticRegression(max_iter=500, multi_class="multinomial",
                              C=1.0, solver="lbfgs")
    meta.fit(stacked_train, y_train)
    ensemble = StackedMetaModel(base_models=base, meta=meta)
    save(ensemble, "ensemble_v1", len(X_train), evaluate("ensemble", ensemble, X_test, y_test))

    base_h = base + [market]
    stacked_train_h = np.hstack([m.predict_proba(X_train) for m in base_h])
    meta_h = LogisticRegression(max_iter=500, multi_class="multinomial",
                                C=0.5, solver="lbfgs")
    meta_h.fit(stacked_train_h, y_train)
    hybrid = StackedMetaModel(base_models=base_h, meta=meta_h)
    save(hybrid, "hybrid_v1", len(X_train), evaluate("hybrid", hybrid, X_test, y_test))

    log.info(f"\n✅ Done. Files in {MODELS_DIR}:")
    for p in sorted(MODELS_DIR.glob("*.pkl")):
        log.info(f"   {p.name:24s}  {p.stat().st_size/1024:7.1f} KB")
    log.info("\nNext: set USE_REAL_ML_MODELS=true and restart the server.")


if __name__ == "__main__":
    main()
