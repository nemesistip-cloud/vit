#!/usr/bin/env python3
"""scripts/populate_sports_data.py — Build sports CSV datasets from public sources.

This script seeds the sports CSV templates under data/sports/ with real and
realistic match records. It uses public tennis and NBA sources, plus MLB's
open stats API, and it synthesizes plausible NFL, EuroLeague, and rugby rows
when public raw feeds are not available in the current environment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import random
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "sports"
DATA_ROOT.mkdir(parents=True, exist_ok=True)

TENNIS_ATP_YEARS = list(range(2000, 2025))
TENNIS_WTA_YEARS = list(range(2010, 2025))

NBA_ELO_URL = "https://raw.githubusercontent.com/fivethirtyeight/data/master/nba-elo/nbaallelo.csv"
ATP_BASE_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{year}.csv"
WTA_BASE_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{year}.csv"

MLB_API_TEMPLATE = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={year}&hydrate=team,linescore,venue"

SYNTHETIC_NFL_TEAMS = [
    "Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens", "Buffalo Bills",
    "Carolina Panthers", "Chicago Bears", "Cincinnati Bengals", "Cleveland Browns",
    "Dallas Cowboys", "Denver Broncos", "Detroit Lions", "Green Bay Packers",
    "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars", "Kansas City Chiefs",
    "Las Vegas Raiders", "Los Angeles Chargers", "Los Angeles Rams", "Miami Dolphins",
    "Minnesota Vikings", "New England Patriots", "New Orleans Saints", "New York Giants",
    "New York Jets", "Philadelphia Eagles", "Pittsburgh Steelers", "San Francisco 49ers",
    "Seattle Seahawks", "Tampa Bay Buccaneers", "Tennessee Titans", "Washington Commanders",
]

SYNTHETIC_RUGBY_TEAMS = [
    "Leicester Tigers", "Exeter Chiefs", "Saracens", "Northampton Saints",
    "Harlequins", "Gloucester", "Bath", "Sale Sharks",
    "Toulouse", "Leinster", "Munster", "Saracens", "Racing 92", "Stade Français",
    "Ulster", "Lyon", "Bordeaux", "Scarlets",
]

EUROLEAGUE_TEAMS = [
    "Real Madrid", "Barcelona", "Fenerbahçe", "Olympiacos", "CSKA Moscow",
    "Maccabi Tel Aviv", "Baskonia", "Anadolu Efes", "Panathinaikos", "Zalgiris Kaunas",
    "Bayern Munich", "Valencia", "Milano", "Partizan", "ASVEL",
]

EXPECTED_HEADERS = {
    "data/sports/basketball/nba_matches.csv": [
        "home_team", "away_team", "home_score", "away_score",
        "home_odds", "away_odds", "date", "season", "league", "venue",
        "attendance", "over_under", "home_rating", "away_rating"
    ],
    "data/sports/basketball/euroleague_matches.csv": [
        "home_team", "away_team", "home_score", "away_score",
        "home_odds", "away_odds", "date", "season", "league", "venue",
        "attendance", "over_under", "home_rating", "away_rating"
    ],
    "data/sports/tennis/atp_matches.csv": [
        "match_date", "tournament", "surface", "best_of",
        "player1", "player2", "player1_rank", "player2_rank",
        "player1_odds", "player2_odds", "result", "winner", "sets", "duration",
        "aces", "double_faults", "first_serve_pct", "break_points_saved", "break_points_converted"
    ],
    "data/sports/tennis/wta_matches.csv": [
        "match_date", "tournament", "surface", "best_of",
        "player1", "player2", "player1_rank", "player2_rank",
        "player1_odds", "player2_odds", "result", "winner", "sets", "duration",
        "aces", "double_faults", "first_serve_pct", "break_points_saved", "break_points_converted"
    ],
    "data/sports/american_football/nfl_matches.csv": [
        "home_team", "away_team", "home_score", "away_score",
        "home_odds", "away_odds", "date", "stadium", "attendance",
        "season", "league", "team_stats_json", "weather", "coach_home", "coach_away"
    ],
    "data/sports/baseball/mlb_matches.csv": [
        "home_team", "away_team", "home_score", "away_score",
        "home_odds", "away_odds", "date", "stadium", "attendance",
        "season", "league", "pitcher_home", "pitcher_away", "weather",
        "runs", "hits", "errors"
    ],
    "data/sports/rugby/rugby_matches.csv": [
        "home_team", "away_team", "home_score", "away_score",
        "home_odds", "away_odds", "date", "stadium", "attendance",
        "season", "league", "tries_home", "tries_away",
        "conversions_home", "conversions_away", "penalties_home", "penalties_away"
    ],
}


def fetch_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def csv_to_dataframe(url: str) -> pd.DataFrame:
    data = fetch_url(url)
    return pd.read_csv(io.BytesIO(data), low_memory=False)


def write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in headers})


def format_date(value: str, source_format: str | None = None) -> str:
    if not value or pd.isna(value):
        return ""
    try:
        if source_format:
            return datetime.strptime(value, source_format).strftime("%Y-%m-%d")
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
        if "/" in value:
            return datetime.strptime(value, "%m/%d/%Y").date().isoformat()
        return datetime.strptime(value, "%Y%m%d").date().isoformat()
    except Exception:
        return value


def safe_float(value: Any) -> float:
    if pd.isna(value):
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def odds_from_rating(home: float, away: float) -> tuple[float, float]:
    if home == away:
        return 1.95, 1.95
    diff = away - home
    p_home = 1.0 / (1.0 + 10 ** (diff / 400.0))
    p_away = 1.0 - p_home
    home_odds = round(max(1.05, min(15.0, 1.0 / max(p_home, 1e-6))), 2)
    away_odds = round(max(1.05, min(15.0, 1.0 / max(p_away, 1e-6))), 2)
    return home_odds, away_odds


def synthesize_probs_from_ranks(rank1: int, rank2: int) -> tuple[float, float]:
    if rank1 <= 0 or rank2 <= 0:
        return 1.8, 1.8
    diff = rank2 - rank1
    p1 = 1 / (1 + 10 ** (diff / 20))
    p1 = max(1e-6, min(1 - 1e-6, p1))
    return round(max(1.05, min(10.0, 1.0 / p1)), 2), round(max(1.05, min(10.0, 1.0 / (1 - p1))), 2)


def normalize_tennis_frame(df: pd.DataFrame, is_atp: bool = True) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, match in df.iterrows():
        if pd.isna(match.get("tourney_date")) or pd.isna(match.get("winner_name")) or pd.isna(match.get("loser_name")):
            continue
        home_rank = safe_int(match.get("winner_rank") or match.get("winner_seed"))
        away_rank = safe_int(match.get("loser_rank") or match.get("loser_seed"))
        odds_home, odds_away = synthesize_probs_from_ranks(home_rank, away_rank)
        score = str(match.get("score") or "")
        sets = len([part for part in score.split() if part and set(part) <= set("0123456789-")])
        minutes = match.get("minutes")
        duration = str(int(minutes)) if not pd.isna(minutes) else ""
        w_ace = safe_float(match.get("w_ace"))
        l_ace = safe_float(match.get("l_ace"))
        w_df = safe_float(match.get("w_df"))
        l_df = safe_float(match.get("l_df"))
        first_serve_pct = ""
        if safe_float(match.get("w_svpt")) > 0:
            first_serve_pct = round(100.0 * safe_float(match.get("w_1stIn")) / safe_float(match.get("w_svpt")), 2)
        bp_saved = safe_float(match.get("w_bpSaved"))
        bp_converted = safe_float(match.get("w_bpFaced")) - bp_saved if not pd.isna(match.get("w_bpFaced")) else ""
        rows.append({
            "match_date": format_date(str(match.get("tourney_date")), source_format="%Y%m%d"),
            "tournament": match.get("tourney_name", ""),
            "surface": match.get("surface", ""),
            "best_of": int(match.get("best_of") or 0),
            "player1": match.get("winner_name", ""),
            "player2": match.get("loser_name", ""),
            "player1_rank": home_rank,
            "player2_rank": away_rank,
            "player1_odds": odds_home,
            "player2_odds": odds_away,
            "result": "player1",
            "winner": "player1",
            "sets": sets,
            "duration": duration,
            "aces": int(w_ace + l_ace),
            "double_faults": int(w_df + l_df),
            "first_serve_pct": first_serve_pct,
            "break_points_saved": bp_saved,
            "break_points_converted": bp_converted,
        })
    return rows


def normalize_nba_frame(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    df = df[df["game_location"] == "H"].copy()
    for _, game in df.iterrows():
        home_rating = safe_float(game.get("elo_i"))
        away_rating = safe_float(game.get("opp_elo_i"))
        home_odds, away_odds = odds_from_rating(home_rating, away_rating)
        rows.append({
            "home_team": game.get("fran_id", ""),
            "away_team": game.get("opp_fran", ""),
            "home_score": int(game.get("pts") or 0),
            "away_score": int(game.get("opp_pts") or 0),
            "home_odds": home_odds,
            "away_odds": away_odds,
            "date": format_date(str(game.get("date_game")), source_format="%m/%d/%Y"),
            "season": int(game.get("year_id") or 0),
            "league": "NBA",
            "venue": game.get("fran_id", ""),
            "attendance": "",
            "over_under": "",
            "home_rating": home_rating,
            "away_rating": away_rating,
        })
    return rows


def normalize_mlb_schedule(year: int) -> list[dict[str, Any]]:
    url = MLB_API_TEMPLATE.format(year=year)
    print(f"Downloading MLB schedule for {year}")
    data = json.loads(fetch_url(url))
    rows: list[dict[str, Any]] = []
    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            status = game.get("status", {}).get("detailedState", "")
            if status.lower() != "final":
                continue
            home = game["teams"]["home"]
            away = game["teams"]["away"]
            home_score = safe_float(home.get("score"))
            away_score = safe_float(away.get("score"))
            home_rating = 1500.0
            away_rating = 1500.0
            home_odds, away_odds = odds_from_rating(home_rating, away_rating)
            linescore = game.get("linescore", {})
            rows.append({
                "home_team": home.get("team", {}).get("name", "") if isinstance(home.get("team"), dict) else home.get("team", ""),
                "away_team": away.get("team", {}).get("name", "") if isinstance(away.get("team"), dict) else away.get("team", ""),
                "home_score": int(home_score),
                "away_score": int(away_score),
                "home_odds": home_odds,
                "away_odds": away_odds,
                "date": format_date(game.get("gameDate", "")),
                "stadium": game.get("venue", {}).get("name", ""),
                "attendance": linescore.get("attendance", ""),
                "season": int(game.get("season") or year),
                "league": "MLB",
                "pitcher_home": "",
                "pitcher_away": "",
                "weather": "",
                "runs": int(home_score + away_score),
                "hits": int(safe_float(linescore.get("teams", {}).get("home", {}).get("hits")) + safe_float(linescore.get("teams", {}).get("away", {}).get("hits"))),
                "errors": int(safe_float(linescore.get("teams", {}).get("home", {}).get("errors")) + safe_float(linescore.get("teams", {}).get("away", {}).get("errors"))),
            })
    return rows


def synthetic_nfl_rows(start_year: int = 2000, end_year: int = 2024) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    random.seed(2026)
    base_date = datetime(start_year, 9, 7)
    coaches = [
        "Tom Brady", "Andy Reid", "Bill Belichick", "Sean Payton",
        "Pete Carroll", "Mike Vrabel", "Mike McCarthy", "John Harbaugh",
        "Sean McVay", "Kyle Shanahan", "Mike Tomlin", "Kevin Stefanski",
    ]
    weather_choices = ["Clear", "Rain", "Cloudy", "Windy", "Snow", "Indoor"]
    team_strength = {team: 1400 + idx * 5 for idx, team in enumerate(SYNTHETIC_NFL_TEAMS)}
    season_date = base_date
    for year in range(start_year, end_year + 1):
        season_date = datetime(year, 9, 7)
        for week in range(1, 18):
            for i in range(0, len(SYNTHETIC_NFL_TEAMS), 2):
                home = SYNTHETIC_NFL_TEAMS[i]
                away = SYNTHETIC_NFL_TEAMS[i + 1]
                home_rating = team_strength[home]
                away_rating = team_strength[away]
                diff = home_rating - away_rating
                home_score = max(10, int(24 + diff / 20 + random.gauss(0, 10)))
                away_score = max(7, int(21 - diff / 20 + random.gauss(0, 10)))
                home_score = max(home_score, 10)
                away_score = max(away_score, 0)
                if away_score >= home_score:
                    away_score = home_score - 1
                home_odds, away_odds = odds_from_rating(home_rating, away_rating)
                rows.append({
                    "home_team": home,
                    "away_team": away,
                    "home_score": home_score,
                    "away_score": away_score,
                    "home_odds": home_odds,
                    "away_odds": away_odds,
                    "date": format_date(season_date.strftime("%Y-%m-%d")),
                    "stadium": f"{home} Stadium",
                    "attendance": int(60000 + random.randint(-5000, 5000)),
                    "season": year,
                    "league": "NFL",
                    "team_stats_json": json.dumps({
                        "yards_home": int(350 + random.gauss(0, 80)),
                        "yards_away": int(330 + random.gauss(0, 80)),
                        "turnovers_home": random.randint(0, 3),
                        "turnovers_away": random.randint(0, 3),
                    }),
                    "weather": random.choice(weather_choices),
                    "coach_home": random.choice(coaches),
                    "coach_away": random.choice(coaches),
                })
                season_date += timedelta(days=2)
    return rows


def synthetic_rugby_rows(start_year: int = 2010, end_year: int = 2024) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    random.seed(1122)
    base_date = datetime(start_year, 2, 1)
    for year in range(start_year, end_year + 1):
        season_date = base_date.replace(year=year)
        for i in range(len(SYNTHETIC_RUGBY_TEAMS) * 2):
            home = SYNTHETIC_RUGBY_TEAMS[i % len(SYNTHETIC_RUGBY_TEAMS)]
            away = SYNTHETIC_RUGBY_TEAMS[(i + 1) % len(SYNTHETIC_RUGBY_TEAMS)]
            tries_home = random.randint(0, 5)
            tries_away = random.randint(0, 5)
            conv_home = min(tries_home, random.randint(0, 3))
            conv_away = min(tries_away, random.randint(0, 3))
            pens_home = random.randint(0, 4)
            pens_away = random.randint(0, 4)
            home_score = tries_home * 5 + conv_home * 2 + pens_home * 3
            away_score = tries_away * 5 + conv_away * 2 + pens_away * 3
            home_odds, away_odds = odds_from_rating(1500 + i * 3, 1500 + ((i + 1) % len(SYNTHETIC_RUGBY_TEAMS)) * 3)
            rows.append({
                "home_team": home,
                "away_team": away,
                "home_score": home_score,
                "away_score": away_score,
                "home_odds": home_odds,
                "away_odds": away_odds,
                "date": format_date(season_date.strftime("%Y-%m-%d")),
                "stadium": f"{home} Stadium",
                "attendance": int(30000 + random.randint(-8000, 8000)),
                "season": year,
                "league": "Rugby",
                "tries_home": tries_home,
                "tries_away": tries_away,
                "conversions_home": conv_home,
                "conversions_away": conv_away,
                "penalties_home": pens_home,
                "penalties_away": pens_away,
            })
            season_date += timedelta(days=3)
    return rows


def synthetic_euroleague_rows(start_year: int = 2015, end_year: int = 2024) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    random.seed(2025)
    for year in range(start_year, end_year + 1):
        season_date = datetime(year, 10, 1)
        for i in range(1000):
            home = EUROLEAGUE_TEAMS[i % len(EUROLEAGUE_TEAMS)]
            away = EUROLEAGUE_TEAMS[(i + 3) % len(EUROLEAGUE_TEAMS)]
            home_rating = 1600 + random.randint(-100, 100)
            away_rating = 1600 + random.randint(-100, 100)
            home_score = int(max(60, 80 + (home_rating - away_rating) / 20 + random.gauss(0, 12)))
            away_score = int(max(60, 78 + (away_rating - home_rating) / 20 + random.gauss(0, 12)))
            home_odds, away_odds = odds_from_rating(home_rating, away_rating)
            rows.append({
                "home_team": home,
                "away_team": away,
                "home_score": home_score,
                "away_score": away_score,
                "home_odds": home_odds,
                "away_odds": away_odds,
                "date": format_date(season_date.strftime("%Y-%m-%d")),
                "season": year,
                "league": "EuroLeague",
                "venue": home,
                "attendance": int(12000 + random.randint(-3000, 3000)),
                "over_under": round((home_score + away_score) * 1.05, 1),
                "home_rating": home_rating,
                "away_rating": away_rating,
            })
            season_date += timedelta(days=2)
    return rows


def populate_sport(path: Path, rows: list[dict[str, Any]]):
    rel = str(path.relative_to(ROOT)).replace(os.sep, "/")
    headers = EXPECTED_HEADERS.get(rel)
    if headers is None:
        raise ValueError(f"No expected header schema for {rel}")
    print(f"Writing {len(rows)} rows to {rel}")
    write_csv(path, headers, rows)


def run_populate():
    print("Populating tennis datasets from JeffSackmann CSVs")
    atp_rows: list[dict[str, Any]] = []
    for year in TENNIS_ATP_YEARS:
        df = csv_to_dataframe(ATP_BASE_URL.format(year=year))
        atp_rows.extend(normalize_tennis_frame(df, is_atp=True))
    populate_sport(DATA_ROOT / "tennis" / "atp_matches.csv", atp_rows)

    wta_rows: list[dict[str, Any]] = []
    for year in TENNIS_WTA_YEARS:
        df = csv_to_dataframe(WTA_BASE_URL.format(year=year))
        wta_rows.extend(normalize_tennis_frame(df, is_atp=False))
    populate_sport(DATA_ROOT / "tennis" / "wta_matches.csv", wta_rows)

    print("Populating NBA dataset from FiveThirtyEight NBA ELO CSV")
    nba_df = csv_to_dataframe(NBA_ELO_URL)
    nba_rows = normalize_nba_frame(nba_df)
    populate_sport(DATA_ROOT / "basketball" / "nba_matches.csv", nba_rows)

    print("Populating EuroLeague with realistic synthetic match records")
    euro_rows = synthetic_euroleague_rows()
    populate_sport(DATA_ROOT / "basketball" / "euroleague_matches.csv", euro_rows)

    print("Populating MLB dataset from MLB Stats API")
    mlb_rows: list[dict[str, Any]] = []
    for year in range(2000, 2025):
        mlb_rows.extend(normalize_mlb_schedule(year))
    populate_sport(DATA_ROOT / "baseball" / "mlb_matches.csv", mlb_rows)

    print("Populating NFL dataset with realistic synthetic game-level rows")
    nfl_rows = synthetic_nfl_rows()
    populate_sport(DATA_ROOT / "american_football" / "nfl_matches.csv", nfl_rows)

    print("Populating Rugby dataset with realistic synthetic rows")
    rugby_rows = synthetic_rugby_rows()
    populate_sport(DATA_ROOT / "rugby" / "rugby_matches.csv", rugby_rows)

    print("Sports datasets populated successfully.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Populate sports CSV datasets from public sources and synthetic rows")
    parser.add_argument("--run", action="store_true", help="Populate all configured sports datasets")
    args = parser.parse_args()
    if args.run:
        return run_populate()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
