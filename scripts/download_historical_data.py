#!/usr/bin/env python3
"""
Download free historical match data from football-data.co.uk and merge
into data/historical_matches.json for model training.

Source: https://www.football-data.co.uk/data.php
No API key required. Run from project root:
    python scripts/download_historical_data.py [--seasons 3] [--dry-run]
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from io import StringIO
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("downloader")

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "historical_matches.json"

# ─── League config ────────────────────────────────────────────────────────────
# (football-data.co.uk code, internal slug, display name)
LEAGUES = [
    ("E0",  "premier_league",  "English Premier League"),
    ("E1",  "championship",    "English Championship"),
    ("SP1", "la_liga",         "Spanish La Liga"),
    ("D1",  "bundesliga",      "German Bundesliga"),
    ("I1",  "serie_a",         "Italian Serie A"),
    ("F1",  "ligue_1",         "French Ligue 1"),
    ("N1",  "eredivisie",      "Dutch Eredivisie"),
    ("B1",  "pro_league",      "Belgian Pro League"),
    ("P1",  "primeira_liga",   "Portuguese Primeira Liga"),
    ("T1",  "super_lig",       "Turkish Süper Lig"),
]

# Seasons available: 9899 through current (2425).
# We download from most recent backwards; --seasons N limits how many.
ALL_SEASONS = [
    "2425", "2324", "2223", "2122", "2021",
    "1920", "1819", "1718", "1617", "1516",
]

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"

# Column mapping: football-data.co.uk → internal field
COL_HOME_GOALS  = ("FTHG", "HG")          # full-time home goals (old files use "HG")
COL_AWAY_GOALS  = ("FTAG", "AG")
COL_DATE        = ("Date",)
COL_HOME_TEAM   = ("HomeTeam",)
COL_AWAY_TEAM   = ("AwayTeam",)
COL_RESULT      = ("FTR",)                 # H/D/A
COL_B365H       = ("B365H",)
COL_B365D       = ("B365D",)
COL_B365A       = ("B365A",)

OUTCOME_MAP = {"H": "home", "D": "draw", "A": "away"}


def _get(row: dict, *keys):
    for k in keys:
        if k in row and row[k].strip():
            return row[k].strip()
    return None


def _season_label(code: str) -> str:
    """'2324' → '2023/24'"""
    return f"20{code[:2]}/20{code[2:]}" if len(code) == 4 else code


def download_csv(league_code: str, season: str, timeout: int = 20) -> list[dict]:
    """Download one season CSV and return parsed row dicts."""
    url = BASE_URL.format(season=season, league=league_code)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VIT-Downloader/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        reader = csv.DictReader(StringIO(raw))
        rows = list(reader)
        # Filter rows that have the minimum required fields
        valid = [r for r in rows if _get(r, *COL_HOME_TEAM) and _get(r, *COL_HOME_GOALS)]
        return valid
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []   # season not available for this league — normal
        log.warning(f"HTTP {e.code} fetching {url}")
        return []
    except Exception as e:
        log.warning(f"Failed {url}: {e}")
        return []


def parse_row(row: dict, league_slug: str, season: str) -> dict | None:
    """Convert a football-data.co.uk CSV row into the training record format."""
    home_team  = _get(row, *COL_HOME_TEAM)
    away_team  = _get(row, *COL_AWAY_TEAM)
    home_goals = _get(row, *COL_HOME_GOALS)
    away_goals = _get(row, *COL_AWAY_GOALS)
    date_str   = _get(row, *COL_DATE)
    result     = _get(row, *COL_RESULT)

    if not all([home_team, away_team, home_goals, away_goals, result]):
        return None

    try:
        hg = int(float(home_goals))
        ag = int(float(away_goals))
    except (ValueError, TypeError):
        return None

    # Parse date — football-data.co.uk uses DD/MM/YY or DD/MM/YYYY
    date_iso = None
    if date_str:
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
            try:
                date_iso = datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue

    # Bookmaker odds (Bet365 preferred; fallback to market average if absent)
    b365h = _get(row, *COL_B365H)
    b365d = _get(row, *COL_B365D)
    b365a = _get(row, *COL_B365A)

    market_odds: dict = {}
    try:
        if b365h and b365d and b365a:
            market_odds = {
                "home": round(float(b365h), 3),
                "draw": round(float(b365d), 3),
                "away": round(float(b365a), 3),
            }
    except (ValueError, TypeError):
        pass

    # Fallback: try other bookmakers in the row
    if not market_odds:
        for h_col, d_col, a_col in [("PSH","PSD","PSA"), ("WHH","WHD","WHA"), ("IWH","IWD","IWA")]:
            try:
                if h_col in row and d_col in row and a_col in row:
                    h, d, a = float(row[h_col] or 0), float(row[d_col] or 0), float(row[a_col] or 0)
                    if h > 0 and d > 0 and a > 0:
                        market_odds = {"home": round(h, 3), "draw": round(d, 3), "away": round(a, 3)}
                        break
            except (ValueError, TypeError):
                continue

    actual_outcome = OUTCOME_MAP.get(result, "")
    total_goals = hg + ag

    record = {
        "home_team":       home_team,
        "away_team":       away_team,
        "league":          league_slug,
        "home_goals":      hg,
        "away_goals":      ag,
        "date":            date_iso or "",
        "season":          _season_label(season),
        "market_odds":     market_odds,
        "actual_outcome":  actual_outcome,
        "total_goals":     total_goals,
        "over_25":         1 if total_goals > 2.5 else 0,
        "over_15":         1 if total_goals > 1.5 else 0,
        "under_25":        1 if total_goals <= 2.5 else 0,
        "btts":            1 if hg > 0 and ag > 0 else 0,
    }

    # Pre-compute vig-free probabilities when odds are present
    if market_odds:
        h_inv = 1 / market_odds["home"]
        d_inv = 1 / market_odds["draw"]
        a_inv = 1 / market_odds["away"]
        total_inv = h_inv + d_inv + a_inv
        if total_inv > 0:
            record["vig_percentage"]  = round((total_inv - 1) * 100, 3)
            record["vig_free_probs"]  = {
                "home": round(h_inv / total_inv, 4),
                "draw": round(d_inv / total_inv, 4),
                "away": round(a_inv / total_inv, 4),
            }

    return record


def load_existing() -> list[dict]:
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Could not load existing data: {e}")
    return []


def dedup_key(record: dict) -> str:
    return f"{record.get('home_team','').lower()}|{record.get('away_team','').lower()}|{record.get('date','')}"


def save(records: list[dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(records, f, indent=2)
    log.info(f"Saved {len(records)} records → {DATA_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download historical match data from football-data.co.uk")
    parser.add_argument("--seasons", type=int, default=5,
                        help="Number of seasons to download per league (default: 5, max: 10)")
    parser.add_argument("--leagues", type=str, default=None,
                        help="Comma-separated league codes to download (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Count what would be downloaded without saving")
    parser.add_argument("--replace-odds-only", action="store_true",
                        help="Only update records that currently have empty market_odds")
    args = parser.parse_args()

    seasons = ALL_SEASONS[:max(1, min(args.seasons, len(ALL_SEASONS)))]
    leagues = LEAGUES
    if args.leagues:
        requested = set(x.strip().upper() for x in args.leagues.split(","))
        leagues = [(c, s, n) for c, s, n in LEAGUES if c in requested]
        if not leagues:
            log.error(f"No matching leagues for {args.leagues}")
            sys.exit(1)

    log.info(f"Downloading {len(leagues)} leagues × {len(seasons)} seasons …")

    existing = load_existing()
    existing_keys: set[str] = {dedup_key(r) for r in existing}
    log.info(f"Existing records: {len(existing)}")

    new_records: list[dict] = []
    updated_count = 0

    # Build lookup dict for updating odds on existing records
    if args.replace_odds_only:
        existing_by_key = {dedup_key(r): r for r in existing}
    else:
        existing_by_key = {}

    for league_code, league_slug, league_name in leagues:
        league_new = 0
        league_updated = 0
        for season in seasons:
            log.info(f"  ↓ {league_name} ({league_code}) · {_season_label(season)}")
            rows = download_csv(league_code, season)
            if not rows:
                continue

            for row in rows:
                record = parse_row(row, league_slug, season)
                if record is None:
                    continue

                key = dedup_key(record)

                if args.replace_odds_only and key in existing_by_key:
                    # Update market_odds on the existing record if it's empty
                    existing_rec = existing_by_key[key]
                    if not existing_rec.get("market_odds") and record.get("market_odds"):
                        existing_rec["market_odds"]    = record["market_odds"]
                        existing_rec["vig_percentage"] = record.get("vig_percentage")
                        existing_rec["vig_free_probs"] = record.get("vig_free_probs")
                        existing_rec["over_25"]        = record["over_25"]
                        existing_rec["over_15"]        = record["over_15"]
                        existing_rec["under_25"]       = record["under_25"]
                        existing_rec["btts"]           = record["btts"]
                        league_updated += 1
                elif key not in existing_keys:
                    new_records.append(record)
                    existing_keys.add(key)
                    league_new += 1

            time.sleep(0.3)   # be polite to the server

        log.info(f"    {league_name}: +{league_new} new, {league_updated} odds-updated")
        updated_count += league_updated

    total_new  = len(new_records)
    log.info(f"\nTotal new records: {total_new} | Odds-updated: {updated_count}")

    if args.dry_run:
        log.info("Dry-run mode — not saving.")
        return

    merged = existing + new_records
    # Sort by date descending so newest data is first (better for training)
    merged.sort(key=lambda r: r.get("date", ""), reverse=True)
    save(merged)
    log.info(f"Done. Training dataset now has {len(merged)} records.")
    log.info(f"Records with real odds: {sum(1 for r in merged if r.get('market_odds'))}")


if __name__ == "__main__":
    main()
