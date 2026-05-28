#!/usr/bin/env python3
"""
scripts/data_audit.py — Sports data validation and manifest audit

Scans the /data/sports directory for CSV datasets, validates schema expectations,
and optionally updates the repository data_manifest.json with actual file metadata.
"""

import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "sports"
MANIFEST_PATH = ROOT / "data_manifest.json"

DEFAULT_MANIFEST = {
    "version": "1.0",
    "generated_at": None,
    "files": []
}

EXPECTED_SCHEMAS = {
    "data/sports/basketball/nba_matches.csv": [
        "home_team", "away_team", "home_score", "away_score",
        "home_odds", "away_odds", "date", "season",
        "league", "venue", "attendance", "over_under",
        "home_rating", "away_rating"
    ],
    "data/sports/basketball/euroleague_matches.csv": [
        "home_team", "away_team", "home_score", "away_score",
        "home_odds", "away_odds", "date", "season",
        "league", "venue", "attendance", "over_under",
        "home_rating", "away_rating"
    ],
    "data/sports/tennis/atp_matches.csv": [
        "match_date", "tournament", "surface", "best_of",
        "player1", "player2", "player1_rank", "player2_rank",
        "player1_odds", "player2_odds", "result", "winner",
        "sets", "duration", "aces", "double_faults",
        "first_serve_pct", "break_points_saved", "break_points_converted"
    ],
    "data/sports/tennis/wta_matches.csv": [
        "match_date", "tournament", "surface", "best_of",
        "player1", "player2", "player1_rank", "player2_rank",
        "player1_odds", "player2_odds", "result", "winner",
        "sets", "duration", "aces", "double_faults",
        "first_serve_pct", "break_points_saved", "break_points_converted"
    ],
    "data/sports/american_football/nfl_matches.csv": [
        "home_team", "away_team", "home_score", "away_score",
        "home_odds", "away_odds", "date", "stadium",
        "attendance", "season", "league", "team_stats_json",
        "weather", "coach_home", "coach_away"
    ],
    "data/sports/baseball/mlb_matches.csv": [
        "home_team", "away_team", "home_score", "away_score",
        "home_odds", "away_odds", "date", "stadium",
        "attendance", "season", "league", "pitcher_home",
        "pitcher_away", "weather", "runs", "hits", "errors"
    ],
    "data/sports/rugby/rugby_matches.csv": [
        "home_team", "away_team", "home_score", "away_score",
        "home_odds", "away_odds", "date", "stadium",
        "attendance", "season", "league", "tries_home",
        "tries_away", "conversions_home", "conversions_away",
        "penalties_home", "penalties_away"
    ],
}

DATE_FIELDS = {"date", "match_date"}


def load_manifest(path: Path):
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def parse_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [
            {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
            for row in reader
        ]
        headers = [h.strip() for h in reader.fieldnames] if reader.fieldnames else []
    return headers, rows


def validate_date(value: str):
    if value is None or value == "":
        return True
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        # support common YYYY-MM-DD formats without timezone
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False


def audit_file(path: Path, expected_columns=None):
    try:
        relpath = str(path.relative_to(ROOT)).replace(os.sep, "/")
    except Exception:
        relpath = str(path)
    headers, rows = parse_csv(path)
    issues = []
    if expected_columns:
        missing = [c for c in expected_columns if c not in headers]
        extra = [c for c in headers if c not in expected_columns]
        if missing:
            issues.append(f"missing columns: {missing}")
        if extra:
            issues.append(f"extra columns: {extra}")
    if not headers:
        issues.append("empty file or missing header row")
    for row_index, row in enumerate(rows, start=2):
        for key in DATE_FIELDS:
            if key in row:
                value = row.get(key, "")
                if value and not validate_date(value):
                    issues.append(f"invalid date in row {row_index}: {key}={value}")
                    break
        if row_index > 1000:
            break
    summary = {
        "path": relpath,
        "row_count": len(rows),
        "columns": headers,
        "expected_columns": expected_columns or [],
        "status": "ok" if not issues else "warning",
        "issues": issues,
    }
    return summary


def collect_csv_files(root: Path):
    return sorted(root.glob("**/*.csv"))


def make_manifest_entry(summary):
    return {
        "path": summary["path"],
        "row_count": summary["row_count"],
        "columns": summary["columns"],
        "expected_columns": summary.get("expected_columns", []),
        "status": summary["status"],
        "issues": summary["issues"],
    }


def main():
    parser = argparse.ArgumentParser(description="Audit sports CSV datasets and optionally update data_manifest.json")
    parser.add_argument("--path", help="Path to a single CSV file to audit")
    parser.add_argument("--update-manifest", action="store_true", help="Regenerate data_manifest.json with current scan metadata")
    args = parser.parse_args()

    if not DATA_ROOT.exists():
        print(f"ERROR: Sports data root not found: {DATA_ROOT}")
        return 1

    targets = []
    if args.path:
        path = Path(args.path)
        if not path.is_absolute():
            path = ROOT / args.path
        if not path.exists():
            print(f"ERROR: file not found: {path}")
            return 1
        targets = [path]
    else:
        targets = collect_csv_files(DATA_ROOT)

    if not targets:
        print("No CSV files found to audit.")
        return 1

    summaries = []
    for path in targets:
        relpath = str(path.relative_to(ROOT)).replace(os.sep, "/")
        expected = EXPECTED_SCHEMAS.get(relpath)
        summary = audit_file(path, expected_columns=expected)
        summaries.append(summary)
        print("-", summary["path"], f"rows={summary['row_count']}", summary["status"])
        if summary["issues"]:
            for issue in summary["issues"]:
                print(f"    • {issue}")

    if args.update_manifest:
        manifest = {"version": "1.0", "generated_at": datetime.utcnow().isoformat() + "Z", "files": [make_manifest_entry(s) for s in summaries]}
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print(f"Updated manifest: {MANIFEST_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
