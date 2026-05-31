"""
scripts/train_models.py — VIT Sports Intelligence Network

Train ensemble models (Logistic Regression, Random Forest, XGBoost, Gradient Boosting)
using historical match data from the database or CSV files. Saves .pkl files to /models/
so the orchestrator can load them with USE_REAL_ML_MODELS=true.

Usage:
    python scripts/train_models.py
    python scripts/train_models.py --source csv --csv path/to/data.csv
    python scripts/train_models.py --source both --csv path/to/data.csv

Requirements (CSV columns):
    Required: home_team, away_team, home_goals, away_goals
    Optional: home_odds, draw_odds, away_odds, league, date, actual_outcome
"""

import argparse
import asyncio
import csv
import logging
import math
import os
import sys
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLUMNS = [
    "home_odds", "draw_odds", "away_odds",
    "home_implied", "draw_implied", "away_implied",
    "lam_h", "lam_a",
    "over_25_implied",
    "strength_ratio",
]

TARGET_MAP = {"home": 0, "draw": 1, "away": 2, "H": 0, "D": 1, "A": 2, "1": 0, "X": 1, "2": 2}


# ── Database fetch ────────────────────────────────────────────────────────────

async def fetch_from_db(db_url: str = None) -> list:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    url = db_url or os.getenv("VIT_DATABASE_URL") or os.getenv("DATABASE_URL") or "sqlite+aiosqlite:///./vit.db"
    # Normalize sync postgres URLs to asyncpg
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    elif url.startswith("postgresql+psycopg2://"):
        url = "postgresql+asyncpg://" + url[len("postgresql+psycopg2://"):]
    # asyncpg does not accept ?sslmode=... in the query string
    if "+asyncpg" in url and "sslmode=" in url:
        from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
        parts = urlsplit(url)
        q = [(k, v) for k, v in parse_qsl(parts.query) if k != "sslmode"]
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))
    logger.info(f"Connecting to: {url.split('@')[-1] if '@' in url else url.split('://')[0]}")

    engine = create_async_engine(url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    rows = []
    async with async_session() as session:
        result = await session.execute(text("""
            SELECT
                home_team, away_team, league,
                opening_odds_home AS home_odds,
                opening_odds_draw AS draw_odds,
                opening_odds_away AS away_odds,
                home_goals, away_goals,
                actual_outcome AS result
            FROM matches
            WHERE actual_outcome IS NOT NULL AND actual_outcome != ''
        """))
        rows = result.fetchall()

    await engine.dispose()
    logger.info(f"Database returned {len(rows)} settled matches")
    return rows


def parse_csv_file(path: str) -> list:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k.strip().lower(): (v or "").strip() for k, v in row.items()})

    logger.info(f"CSV loaded: {len(rows)} rows from {path.name}")
    logger.info(f"Columns detected: {list(rows[0].keys()) if rows else '(empty)'}")
    return rows


def _resolve_result(row_dict, hg, ag):
    for key in ("actual_outcome", "result", "outcome", "ftr", "ft_result"):
        v = str(row_dict.get(key, "")).strip().upper()
        if v in ("H", "HOME", "1"):    return "home"
        if v in ("D", "DRAW", "X"):    return "draw"
        if v in ("A", "AWAY", "2"):    return "away"
    if hg is not None and ag is not None:
        if hg > ag:  return "home"
        if hg == ag: return "draw"
        return "away"
    return None


def build_features_from_dicts(rows: list):
    X, y = [], []
    skipped = 0
    for row in rows:
        def g(*keys, default=None):
            for k in keys:
                v = row.get(k, "")
                if v not in ("", None): return v
            return default

        try:
            hg_raw = g("home_goals", "hg", "fthg")
            ag_raw = g("away_goals", "ag", "ftag")
            hg = int(float(hg_raw)) if hg_raw not in (None, "") else None
            ag = int(float(ag_raw)) if ag_raw not in (None, "") else None
        except (ValueError, TypeError):
            hg = ag = None

        result = _resolve_result(row, hg, ag)
        if result is None:
            skipped += 1
            continue

        try:
            ho  = float(g("home_odds", "b365h", "psh", "whh") or 0)
            do_ = float(g("draw_odds", "b365d", "psd", "whd") or 0)
            ao  = float(g("away_odds", "b365a", "psa", "wha") or 0)
        except (ValueError, TypeError):
            ho = do_ = ao = 0.0

        feat = _make_feature_row(ho, do_, ao, result)
        if feat is None:
            skipped += 1
            continue
        X.append(feat)
        y.append(TARGET_MAP[result])

    if skipped:
        logger.warning(f"Skipped {skipped} invalid rows during feature extraction")
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)


def build_features_from_tuples(rows: list):
    X, y = [], []
    skipped = 0
    for row in rows:
        try:
            ho, do_, ao = float(row[3] or 0), float(row[4] or 0), float(row[5] or 0)
            hg = int(row[6]) if row[6] is not None else None
            ag = int(row[7]) if row[7] is not None else None
            result_raw = str(row[8] or "").strip()
            result = _resolve_result({"actual_outcome": result_raw}, hg, ag)
        except Exception:
            skipped += 1
            continue

        if result is None:
            skipped += 1
            continue

        feat = _make_feature_row(ho, do_, ao, result)
        if feat is None:
            skipped += 1
            continue
        X.append(feat)
        y.append(TARGET_MAP[result])

    if skipped:
        logger.warning(f"Skipped {skipped} invalid rows from database")
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)


def _make_feature_row(ho, do_, ao, result):
    if ho < 1.01: ho = 2.30
    if do_ < 1.01: do_ = 3.30
    if ao < 1.01: ao = 3.10
    inv = (1/ho) + (1/do_) + (1/ao)
    if inv <= 0: return None
    hi, di, ai = (1/ho)/inv, (1/do_)/inv, (1/ao)/inv
    lam_h = max(0.3, -np.log(max(1e-9, 1-hi)) * 1.5)
    lam_a = max(0.3, -np.log(max(1e-9, 1-ai)) * 1.3)
    lam_sum = lam_h + lam_a
    if lam_sum < 20:
        p_under3 = np.exp(-lam_sum) * sum((lam_sum**k)/math.factorial(k) for k in range(3))
        over_25 = 1.0 - p_under3
    else:
        over_25 = 0.65
    strength_ratio = lam_h / max(0.1, lam_a)
    return [ho, do_, ao, hi, di, ai, lam_h, lam_a, over_25, strength_ratio]


def synthetic_bootstrap(n: int = 3000):
    logger.warning("Using synthetic bootstrap — upload real historical CSV for production accuracy")
    rng = np.random.default_rng(42)
    ho  = rng.uniform(1.5, 6.0, n)
    do_ = rng.uniform(2.8, 4.5, n)
    ao  = rng.uniform(1.5, 6.0, n)
    inv = 1/ho + 1/do_ + 1/ao
    hi, di, ai = 1/ho/inv, 1/do_/inv, 1/ao/inv
    lam_h = np.clip(-np.log(np.maximum(1e-9, 1-hi))*1.5, 0.3, 4.0)
    lam_a = np.clip(-np.log(np.maximum(1e-9, 1-ai))*1.3, 0.3, 4.0)
    lam_sum = lam_h + lam_a
    over_25 = np.clip(0.45 + (lam_sum - 2.5)*0.12, 0.2, 0.85)
    strength_ratio = lam_h / np.maximum(0.1, lam_a)
    X = np.column_stack([ho, do_, ao, hi, di, ai, lam_h, lam_a, over_25, strength_ratio]).astype(np.float32)
    diff = hi - ai
    y = np.where(diff > 0.08, 0, np.where(np.abs(diff) <= 0.08, 1, 2)).astype(np.int32)
    noise = rng.integers(0, 3, n)
    mask = rng.random(n) < 0.25
    y[mask] = noise[mask]
    return X, y


def build_model_registry():
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler

    entries = [
        {"key": "logistic_v1", "model": LogisticRegression(max_iter=2000, C=0.5, solver="lbfgs", random_state=42, n_jobs=-1),                                       "scaler": StandardScaler(), "desc": "Logistic Regression (fast baseline)"},
        {"key": "rf_v1",       "model": RandomForestClassifier(n_estimators=300, max_depth=8, min_samples_leaf=5, random_state=42, n_jobs=-1),                      "scaler": None,             "desc": "Random Forest (nonlinear ensemble)"},
        {"key": "gbm_v1",      "model": GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42),                             "scaler": None,             "desc": "Gradient Boosting (Elo-style)"},
    ]

    try:
        from xgboost import XGBClassifier
        entries.append({"key": "xgb_v1",  "model": XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05, eval_metric="mlogloss", random_state=42, verbosity=0, n_jobs=-1), "scaler": None, "desc": "XGBoost"})
    except ImportError:
        logger.info("xgboost not available — install with: pip install xgboost")

    try:
        from lightgbm import LGBMClassifier
        entries.append({"key": "lgbm_v1", "model": LGBMClassifier(n_estimators=300, max_depth=5, learning_rate=0.05, random_state=42, verbose=-1, n_jobs=-1), "scaler": None, "desc": "LightGBM"})
    except (ImportError, OSError) as e:
        logger.info(f"lightgbm not available ({type(e).__name__}); skipping")

    return entries


def train_and_save(entry, X, y):
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    from sklearn.metrics import log_loss as _log_loss

    key   = entry["key"]
    model = entry["model"]
    scaler = entry.get("scaler")
    desc  = entry.get("desc", key)

    logger.info(f"\n  [{key}] {desc}")
    X_fit = scaler.fit_transform(X) if scaler else X

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    acc_scores = cross_val_score(model, X_fit, y, cv=cv, scoring="accuracy", n_jobs=-1)
    acc = float(acc_scores.mean())
    logger.info(f"  [{key}] 5-fold CV accuracy: {acc:.4f} ± {acc_scores.std():.4f}")

    model.fit(X_fit, y)

    try:
        proba = model.predict_proba(X_fit)
        ll = float(_log_loss(y, proba))
    except Exception:
        ll = None

    payload = {
        "model":            model,
        "scaler":           scaler,
        "feature_columns":  FEATURE_COLUMNS,
        "training_samples": len(y),
        "class_labels":     ["home", "draw", "away"],
        "version":          "2.0.0",
        "metrics": {
            "accuracy": acc,
            "cv_std":   float(acc_scores.std()),
            "log_loss": ll,
        },
    }

    out_path = MODELS_DIR / f"{key}.pkl"
    joblib.dump(payload, out_path)
    logger.info(f"  [{key}] ✅ Saved → {out_path}")
    return {"key": key, "accuracy": acc, "log_loss": ll}


async def main(args):
    logger.info("=" * 58)
    logger.info("  VIT Sports Intelligence — Model Training")
    logger.info("=" * 58)

    all_rows, is_dict = [], False

    if args.source in ("db", "both"):
        try:
            db_rows = await fetch_from_db(args.db_url)
            all_rows.extend(db_rows)
        except Exception as e:
            logger.warning(f"DB fetch failed: {e}")

    if args.source in ("csv", "both") and args.csv:
        try:
            csv_rows = parse_csv_file(args.csv)
            all_rows.extend(csv_rows)
            is_dict = True
        except Exception as e:
            logger.error(f"CSV failed: {e}")

    logger.info(f"\nTotal raw rows: {len(all_rows)}")

    if len(all_rows) < 50:
        logger.warning("Insufficient real data — using synthetic bootstrap")
        X, y = synthetic_bootstrap(3000)
    else:
        try:
            X, y = (build_features_from_dicts(all_rows) if is_dict
                    else build_features_from_tuples(all_rows))
            if len(X) < 50:
                raise ValueError("Too few usable rows")
        except (ValueError, Exception) as e:
            logger.warning(f"Feature build issue: {e} — using synthetic bootstrap")
            X, y = synthetic_bootstrap(3000)

    logger.info(f"\nFeature matrix: {len(X)} samples × {X.shape[1]} features")
    logger.info(f"Classes: home={sum(y==0)}, draw={sum(y==1)}, away={sum(y==2)}")

    results = []
    for entry in build_model_registry():
        try:
            r = train_and_save(entry, X, y)
            results.append(r)
        except Exception as e:
            logger.error(f"  [{entry['key']}] FAILED: {e}")

    logger.info("\n" + "=" * 58)
    logger.info("  Results Summary")
    logger.info("=" * 58)
    for r in sorted(results, key=lambda x: x["accuracy"], reverse=True):
        ll_str = f"  log_loss={r['log_loss']:.4f}" if r["log_loss"] is not None else ""
        logger.info(f"  {r['key']:20s}  accuracy={r['accuracy']:.4f}{ll_str}")

    logger.info(f"\nModels saved to: {MODELS_DIR}/")
    logger.info("Next: set USE_REAL_ML_MODELS=true in .env and restart the server.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VIT Model Training")
    parser.add_argument("--source", choices=["db", "csv", "both"], default="db")
    parser.add_argument("--csv", type=str, default=None, help="Path to CSV file")
    parser.add_argument("--db-url", type=str, default=None, help="Override database URL")
    args = parser.parse_args()
    if args.source in ("csv", "both") and not args.csv:
        parser.error("--csv is required when --source is csv or both")
    asyncio.run(main(args))
