#!/usr/bin/env python3
"""
VIT Sports Analytics Network — Large Dataset Builder
Merges all available CSVs into one unified historical_matches.json
for ensemble model training.

Sources:
  data/raw/           — Football-Data.org CSVs (2018-2025, 8 leagues)
  data/uploads/       — Pre-processed multi-league CSVs
  data/historical_matches_training.csv — Existing processed data
"""
import csv
import json
import os
import sys
from datetime import datetime
from typing import Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT, "data")
OUT_FILE = os.path.join(DATA_DIR, "historical_matches.json")

# Football-Data.org Div → league name
DIV_MAP = {
    "E0":  "premier_league",
    "E1":  "championship",
    "D1":  "bundesliga",
    "SP1": "la_liga",
    "I1":  "serie_a",
    "F1":  "ligue_1",
    "N1":  "eredivisie",
    "P1":  "primeira_liga",
    "B1":  "belgian_pro_league",
    "SC0": "scottish_premiership",
    "T1":  "super_lig",
    "G1":  "super_league_greece",
}

# Upload CSV "league" strings that need normalising
UPLOAD_LEAGUE_MAP = {
    "Premier League": "premier_league",
    "EPL": "premier_league",
    "La Liga": "la_liga",
    "Bundesliga": "bundesliga",
    "Serie A": "serie_a",
    "Ligue 1": "ligue_1",
    "Eredivisie": "eredivisie",
    "Primeira Liga": "primeira_liga",
    "Scottish Premiership": "scottish_premiership",
    "Belgian Pro League": "belgian_pro_league",
    "Super Lig": "super_lig",
    "Champions League": "champions_league",
    "Europa League": "europa_league",
    "MLS": "mls",
}


def _outcome(hg: int, ag: int) -> str:
    if hg > ag: return "home"
    if hg < ag: return "away"
    return "draw"


def _enrich(rec: dict) -> dict:
    hg = int(rec.get("home_goals", 0) or 0)
    ag = int(rec.get("away_goals", 0) or 0)
    total = hg + ag
    rec["total_goals"] = total
    rec["over_25"]  = 1 if total > 2.5 else 0
    rec["over_15"]  = 1 if total > 1.5 else 0
    rec["under_25"] = 1 if total <= 2.5 else 0
    rec["btts"]     = 1 if (hg > 0 and ag > 0) else 0
    odds = rec.get("market_odds") or {}
    if odds:
        try:
            total_inv = sum(1.0 / v for v in odds.values() if isinstance(v, (int, float)) and v > 0)
            if total_inv > 0:
                rec["vig_percentage"] = round((total_inv - 1) * 100, 4)
                rec["vig_free_probs"] = {
                    k: round((1.0 / v) / total_inv, 4)
                    for k, v in odds.items()
                    if isinstance(v, (int, float)) and v > 0
                }
        except Exception:
            pass
    return rec


def _parse_date_raw(date_str: str) -> str:
    """Convert DD/MM/YYYY → YYYY-MM-DD"""
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        try:
            return datetime.strptime(date_str.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
        except Exception:
            return date_str.strip()


def _season_from_date(date_str: str) -> str:
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        if d.month >= 7:
            return f"{d.year}/{d.year + 1}"
        return f"{d.year - 1}/{d.year}"
    except Exception:
        return "unknown"


def load_raw_csvs() -> list:
    """Load Football-Data.org CSVs from data/raw/"""
    raw_dir = os.path.join(DATA_DIR, "raw")
    records = []
    if not os.path.isdir(raw_dir):
        print("  [raw] No data/raw directory found")
        return records

    for fname in sorted(os.listdir(raw_dir)):
        if not fname.endswith(".csv"):
            continue
        fpath = os.path.join(raw_dir, fname)
        file_records = 0
        try:
            with open(fpath, encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Skip empty rows
                    if not row.get("HomeTeam") or not row.get("FTHG"):
                        continue
                    try:
                        hg = int(float(row["FTHG"]))
                        ag = int(float(row["FTAG"]))
                    except (ValueError, TypeError):
                        continue

                    div = row.get("Div", "").strip()
                    league = DIV_MAP.get(div, div.lower() or "unknown")
                    date_raw = row.get("Date", "")
                    date_str = _parse_date_raw(date_raw)
                    season = _season_from_date(date_str)

                    h_odds = row.get("B365H") or row.get("AvgH") or row.get("BWH")
                    d_odds = row.get("B365D") or row.get("AvgD") or row.get("BWD")
                    a_odds = row.get("B365A") or row.get("AvgA") or row.get("BWA")

                    try:
                        h_odds = float(h_odds) if h_odds else None
                        d_odds = float(d_odds) if d_odds else None
                        a_odds = float(a_odds) if a_odds else None
                    except (ValueError, TypeError):
                        h_odds = d_odds = a_odds = None

                    market_odds = {}
                    if h_odds and h_odds > 1.0: market_odds["home"] = round(h_odds, 3)
                    if d_odds and d_odds > 1.0: market_odds["draw"] = round(d_odds, 3)
                    if a_odds and a_odds > 1.0: market_odds["away"] = round(a_odds, 3)

                    ftr = row.get("FTR", "").strip()
                    outcome = {"H": "home", "D": "draw", "A": "away"}.get(ftr, _outcome(hg, ag))

                    rec = {
                        "home_team":      row["HomeTeam"].strip(),
                        "away_team":      row["AwayTeam"].strip(),
                        "league":         league,
                        "home_goals":     hg,
                        "away_goals":     ag,
                        "date":           date_str,
                        "season":         season,
                        "market_odds":    market_odds,
                        "actual_outcome": outcome,
                        "source":         f"football_data_{fname}",
                    }
                    records.append(_enrich(rec))
                    file_records += 1
        except Exception as e:
            print(f"  [raw] Error loading {fname}: {e}")
            continue
        print(f"  [raw] {fname}: {file_records} records")
    return records


def load_uploads() -> list:
    """Load upload CSVs from data/uploads/ — mixed formats"""
    uploads_dir = os.path.join(DATA_DIR, "uploads")
    records = []
    if not os.path.isdir(uploads_dir):
        return records

    for fname in sorted(os.listdir(uploads_dir)):
        if not fname.endswith(".csv"):
            continue
        fpath = os.path.join(uploads_dir, fname)
        file_records = 0
        try:
            with open(fpath, encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                for row in reader:
                    # Format A: home_team,away_team,home_goals,away_goals,actual_outcome,league,date,...
                    if "home_team" in fieldnames and "home_goals" in fieldnames:
                        ht = row.get("home_team", "").strip()
                        at = row.get("away_team", "").strip()
                        if not ht or not at:
                            continue
                        try:
                            hg = int(float(row.get("home_goals", 0) or 0))
                            ag = int(float(row.get("away_goals", 0) or 0))
                        except (ValueError, TypeError):
                            continue
                        raw_league = row.get("league", "unknown").strip()
                        league = UPLOAD_LEAGUE_MAP.get(raw_league, raw_league.lower().replace(" ", "_"))
                        date_str = row.get("date", "").strip()
                        if not date_str:
                            continue
                        season = row.get("season", _season_from_date(date_str))

                        h_odds = row.get("B365H") or row.get("home_odds")
                        d_odds = row.get("B365D") or row.get("draw_odds")
                        a_odds = row.get("B365A") or row.get("away_odds")
                        try:
                            h_odds = float(h_odds) if h_odds else None
                            d_odds = float(d_odds) if d_odds else None
                            a_odds = float(a_odds) if a_odds else None
                        except (ValueError, TypeError):
                            h_odds = d_odds = a_odds = None

                        market_odds = {}
                        if h_odds and h_odds > 1.0: market_odds["home"] = round(h_odds, 3)
                        if d_odds and d_odds > 1.0: market_odds["draw"] = round(d_odds, 3)
                        if a_odds and a_odds > 1.0: market_odds["away"] = round(a_odds, 3)

                        raw_out = row.get("actual_outcome", "").strip()
                        outcome_map = {"H": "home", "D": "draw", "A": "away",
                                       "home": "home", "draw": "draw", "away": "away"}
                        outcome = outcome_map.get(raw_out, _outcome(hg, ag))

                        rec = {
                            "home_team":      ht,
                            "away_team":      at,
                            "league":         league,
                            "home_goals":     hg,
                            "away_goals":     ag,
                            "date":           date_str,
                            "season":         season,
                            "market_odds":    market_odds,
                            "actual_outcome": outcome,
                            "source":         f"upload_{fname[:8]}",
                        }
                        records.append(_enrich(rec))
                        file_records += 1

                    # Format B: HomeTeam,AwayTeam,FTHG,FTAG,FTR,... (Football-Data format in uploads)
                    elif "HomeTeam" in fieldnames and "FTHG" in fieldnames:
                        ht = row.get("HomeTeam", "").strip()
                        at = row.get("AwayTeam", "").strip()
                        if not ht or not at:
                            continue
                        try:
                            hg = int(float(row["FTHG"] or 0))
                            ag = int(float(row["FTAG"] or 0))
                        except (ValueError, TypeError):
                            continue
                        div = row.get("Div", "").strip()
                        league = DIV_MAP.get(div, "unknown")
                        date_raw = row.get("Date", "")
                        date_str = _parse_date_raw(date_raw)
                        season = _season_from_date(date_str)

                        h_odds = row.get("B365H") or row.get("AvgH")
                        d_odds = row.get("B365D") or row.get("AvgD")
                        a_odds = row.get("B365A") or row.get("AvgA")
                        try:
                            h_odds = float(h_odds) if h_odds else None
                            d_odds = float(d_odds) if d_odds else None
                            a_odds = float(a_odds) if a_odds else None
                        except (ValueError, TypeError):
                            h_odds = d_odds = a_odds = None

                        market_odds = {}
                        if h_odds and h_odds > 1.0: market_odds["home"] = round(h_odds, 3)
                        if d_odds and d_odds > 1.0: market_odds["draw"] = round(d_odds, 3)
                        if a_odds and a_odds > 1.0: market_odds["away"] = round(a_odds, 3)

                        ftr = row.get("FTR", "").strip()
                        outcome = {"H": "home", "D": "draw", "A": "away"}.get(ftr, _outcome(hg, ag))

                        rec = {
                            "home_team":      ht,
                            "away_team":      at,
                            "league":         league,
                            "home_goals":     hg,
                            "away_goals":     ag,
                            "date":           date_str,
                            "season":         season,
                            "market_odds":    market_odds,
                            "actual_outcome": outcome,
                            "source":         f"upload_fd_{fname[:8]}",
                        }
                        records.append(_enrich(rec))
                        file_records += 1

        except Exception as e:
            print(f"  [upload] Error loading {fname}: {e}")
            continue
        if file_records > 0:
            print(f"  [upload] {fname[:40]}: {file_records} records")
    return records


def load_existing_json() -> list:
    """Load existing historical_matches.json"""
    if not os.path.exists(OUT_FILE):
        return []
    try:
        with open(OUT_FILE) as f:
            data = json.load(f)
        print(f"  [json] Existing historical_matches.json: {len(data)} records")
        return data
    except Exception as e:
        print(f"  [json] Error loading existing JSON: {e}")
        return []


def deduplicate(records: list) -> list:
    """Deduplicate by (home_team, away_team, date, league)"""
    seen = set()
    out = []
    dups = 0
    for r in records:
        key = (
            str(r.get("home_team", "")).strip().lower(),
            str(r.get("away_team", "")).strip().lower(),
            str(r.get("date", ""))[:10],
            str(r.get("league", "")).strip().lower(),
        )
        if key in seen:
            dups += 1
            continue
        seen.add(key)
        out.append(r)
    print(f"  [dedup] Removed {dups} duplicates → {len(out)} unique records")
    return out


def filter_valid(records: list) -> list:
    """Remove records with missing essential fields"""
    valid = []
    for r in records:
        if (r.get("home_team") and r.get("away_team")
                and r.get("date") and r.get("actual_outcome")
                and r.get("home_goals") is not None
                and r.get("away_goals") is not None):
            valid.append(r)
    print(f"  [filter] {len(valid)} valid records (from {len(records)})")
    return valid


def build_dataset():
    print("=" * 60)
    print("VIT Sports — Training Dataset Builder")
    print("=" * 60)
    all_records = []

    print("\n[1] Loading raw Football-Data.org CSVs...")
    raw = load_raw_csvs()
    print(f"    Subtotal: {len(raw)} records")
    all_records.extend(raw)

    print("\n[2] Loading upload CSVs...")
    uploads = load_uploads()
    print(f"    Subtotal: {len(uploads)} records")
    all_records.extend(uploads)

    print("\n[3] Loading existing JSON (for continuity)...")
    existing = load_existing_json()
    existing_count = len(existing)
    # Merge existing records so we keep TheSportsDB + any other prior source
    all_records.extend(existing)

    print("\n[4] Filtering & deduplicating...")
    all_records = filter_valid(all_records)
    all_records = deduplicate(all_records)

    # Sort by date descending (most recent first for better training signal)
    all_records.sort(key=lambda r: r.get("date", ""), reverse=True)

    print(f"\n[5] Writing {len(all_records)} records to {OUT_FILE}...")
    with open(OUT_FILE, "w") as f:
        json.dump(all_records, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"DONE — {len(all_records)} training samples written")
    print(f"  Previously: {existing_count} records")
    print(f"  Now:        {len(all_records)} records")
    print(f"  Gain:       +{len(all_records) - existing_count}")
    leagues = {}
    for r in all_records:
        l = r.get("league", "unknown")
        leagues[l] = leagues.get(l, 0) + 1
    print("\nLeague breakdown:")
    for league, count in sorted(leagues.items(), key=lambda x: -x[1]):
        print(f"  {league:30s}: {count:5d}")
    print("=" * 60)
    return len(all_records)


if __name__ == "__main__":
    build_dataset()
