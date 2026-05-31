#!/usr/bin/env python3
"""
scripts/train_model.py — Unified sport-specific training entrypoint

Usage:
    python3 scripts/train_model.py --sport basketball --csv data/sports/basketball/nba_matches.csv
    python3 scripts/train_model.py --sport tennis --csv data/sports/tennis/atp_matches.csv
    python3 scripts/train_model.py --sport rugby --csv data/sports/rugby/rugby_matches.csv
"""

import argparse
import csv
import json
import logging
import os
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.dummy import DummyClassifier

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "sports"
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train_model")

MANIFEST_PATH = ROOT / "data_manifest.json"

def load_manifest(manifest_path: Path = None):
    path = manifest_path or MANIFEST_PATH
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception:
        return {}
    mapping = {}
    for entry in manifest.get("files", []):
        sport = entry.get("sport") or ""
        rel = entry.get("path")
        expected = entry.get("expected_columns") or []
        if sport:
            mapping.setdefault(sport, []).append({"path": rel, "expected": expected})
    return mapping

TARGET_FIELDS = ["result", "winner", "actual_outcome", "outcome", "ftr", "ft_result"]
NON_NUMERIC_COLUMNS = {
    "home_team", "away_team", "date", "match_date", "tournament",
    "surface", "player1", "player2", "result", "winner",
    "league", "venue", "stadium", "weather", "team_stats_json",
    "pitcher_home", "pitcher_away"
}


def resolve_target(row):
    if row is None:
        return None
    for key in TARGET_FIELDS:
        value = row.get(key)
        if value is None:
            continue
        norm = str(value).strip().upper()
        if norm in {"H", "HOME", "1"}:
            return "home"
        if norm in {"A", "AWAY", "2"}:
            return "away"
        if norm in {"D", "DRAW", "X"}:
            return "draw"
        if norm in {"PLAYER1", "P1", "1"}:
            return "player1"
        if norm in {"PLAYER2", "P2", "2"}:
            return "player2"
        if norm in {"PLAYER 1", "PLAYER 2"}:
            return norm.replace(" ", "").lower()
    return None


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader]
        headers = reader.fieldnames or []
    return headers, rows


def numeric_value(value):
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def build_feature_matrix(rows, sport, headers=None, expected_columns=None):
    """
    Build a numeric feature matrix from rows.

    Preference order:
    - If `expected_columns` provided (from manifest), extract numeric values in that order.
    - Otherwise fall back to heuristic column patterns.
    """
    X = []
    y = []
    for row in rows:
        target = resolve_target(row)
        if target is None:
            continue
        features = []

        if expected_columns:
            for col in expected_columns:
                if col in row and col not in NON_NUMERIC_COLUMNS:
                    features.append(numeric_value(row.get(col)))
            # If no numeric features found from expected columns, fall back to heuristics
        if not features:
            # Generic numeric feature extraction based on common column patterns
            for col in ("home_odds", "away_odds", "draw_odds"):
                if col in row:
                    features.append(numeric_value(row.get(col)))
            for col in ("home_score", "away_score", "home_goals", "away_goals"):
                if col in row:
                    features.append(numeric_value(row.get(col)))
            for col in ("over_under", "attendance"):
                if col in row:
                    features.append(numeric_value(row.get(col)))
            for col in ("player1_rank", "player2_rank", "home_rating", "away_rating"):
                if col in row:
                    features.append(numeric_value(row.get(col)))
            # Fallback: include heuristic-matching headers up to 6
            if headers:
                for h in headers:
                    if len(features) >= 6:
                        break
                    if any(k in h.lower() for k in ("odds", "score", "rank", "rating", "attendance", "over")):
                        features.append(numeric_value(row.get(h)))

        if not features:
            continue

        X.append(features)
        y.append(target)

    if not X:
        return np.array([], dtype=np.float32), np.array([])
    return np.array(X, dtype=np.float32), np.array(y)


def encode_target(y):
    labels = sorted(set(y))
    mapping = {label: idx for idx, label in enumerate(labels)}
    return np.array([mapping[label] for label in y], dtype=np.int32), mapping


def build_baseline_model(X, y):
    if len(X) == 0:
        return None, None
    clf = LogisticRegression(max_iter=500, solver="lbfgs")
    clf.fit(X, y)
    return clf, clf.predict(X)


def summarize(rows, headers, path):
    print(f"Dataset: {path}")
    print(f"  rows: {len(rows)}")
    print(f"  columns: {headers}")
    if len(rows) > 0:
        print(f"  sample row: {rows[0]}")


def main():
    parser = argparse.ArgumentParser(description="Train sport-specific models from CSV data")
    parser.add_argument("--sport", required=True, help="Sport dataset to train")
    parser.add_argument("--csv", required=True, help="Path to source CSV dataset")
    parser.add_argument("--output", default=None, help="Output model file path")
    args = parser.parse_args()

    path = Path(args.csv)
    if not path.is_absolute():
        path = ROOT / args.csv
    if not path.exists():
        logger.error("CSV not found: %s", path)
        return 1

    headers, rows = load_csv(path)
    manifest_map = load_manifest()
    # If a manifest entry exists for sport, warn if expected columns missing
    sport_entries = manifest_map.get(args.sport, [])
    if sport_entries:
        # pick first matching CSV entry
        expected = sport_entries[0].get("expected", [])
        missing = [c for c in expected if c not in headers]
        if missing:
            logger.warning("Dataset headers do not include expected columns from manifest: %s", missing)

    summarize(rows, headers, path)

    expected_columns = []
    if sport_entries:
        expected_columns = sport_entries[0].get("expected", [])
    X, y_raw = build_feature_matrix(rows, args.sport, headers=headers, expected_columns=expected_columns)
    if len(X) == 0:
        logger.error("No valid rows with target labels found. Ensure the CSV contains result/outcome data.")
        return 1

    y_encoded, mapping = encode_target(y_raw)
    unique_classes = np.unique(y_encoded)
    if len(unique_classes) < 2:
        logger.warning("Only one target class found — training a trivial DummyClassifier")
        clf = DummyClassifier(strategy="most_frequent")
        clf.fit(X, y_encoded)
        y_pred = clf.predict(X)
        model = clf
    else:
        model, y_pred = build_baseline_model(X, y_encoded)
        if model is None:
            logger.error("Failed to train a baseline model")
            return 1

    accuracy = accuracy_score(y_encoded, y_pred)
    logger.info("Trained baseline model for %s: accuracy=%.4f on %d rows", args.sport, accuracy, len(X))
    logger.info("  target mapping: %s", mapping)

    model_file = Path(args.output) if args.output else MODELS_DIR / f"{args.sport}_baseline.pkl"
    joblib.dump({"model": model, "mapping": mapping, "features": headers}, model_file)
    logger.info("Saved model to %s", model_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
