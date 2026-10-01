#!/usr/bin/env python3
"""Refresh recent NBA team results from ESPN's public schedule API."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data/sports/basketball/nba_recent_espn_matches.csv"
BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"
FIELDS = (
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "date",
    "season",
    "league",
    "source",
    "source_url",
    "external_id",
)


def _score(competitor: dict[str, Any]) -> int | None:
    raw = competitor.get("score")
    if isinstance(raw, dict):
        raw = raw.get("value", raw.get("displayValue"))
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _fetch_team_schedule(team_code: str, season: int) -> tuple[list[dict], str]:
    url = f"{BASE_URL}/{team_code}/schedule?season={season}"
    with urllib.request.urlopen(url, timeout=25) as response:
        payload = json.load(response)

    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    for event in payload.get("events", []):
        try:
            played_at = datetime.fromisoformat(
                str(event.get("date", "")).replace("Z", "+00:00")
            ).astimezone(timezone.utc)
        except ValueError:
            continue
        if played_at >= now:
            continue

        for competition in event.get("competitions", []):
            status = competition.get("status", {}).get("type", {})
            competitors = competition.get("competitors", [])
            if not status.get("completed") or len(competitors) != 2:
                continue
            home = next((item for item in competitors if item.get("homeAway") == "home"), None)
            away = next((item for item in competitors if item.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            home_score = _score(home)
            away_score = _score(away)
            if home_score is None or away_score is None:
                continue

            rows.append({
                "home_team": home.get("team", {}).get("displayName", ""),
                "away_team": away.get("team", {}).get("displayName", ""),
                "home_score": home_score,
                "away_score": away_score,
                "date": played_at.isoformat(),
                "season": str(season),
                "league": "NBA",
                "source": "espn_public_api",
                "source_url": url,
                "external_id": str(event.get("id", "")),
            })

    rows.sort(key=lambda row: row["date"], reverse=True)
    return rows, url


def refresh(teams: list[str], season: int, games_per_team: int, output: Path) -> dict:
    unique_rows: dict[str, dict] = {}
    per_team: dict[str, int] = {}
    for team_code in teams:
        rows, _ = _fetch_team_schedule(team_code.lower(), season)
        selected = rows[:games_per_team]
        if not selected:
            raise RuntimeError(f"ESPN returned no completed scored games for {team_code}")
        per_team[team_code.lower()] = len(selected)
        for row in selected:
            identity = row["external_id"] or "|".join(
                (row["date"], row["home_team"], row["away_team"])
            )
            unique_rows[identity] = row

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="", dir=output.parent, delete=False
        ) as handle:
            temporary_path = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(sorted(
                unique_rows.values(), key=lambda row: row["date"], reverse=True
            ))
        os.replace(temporary_path, output)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()

    return {
        "output": str(output),
        "source": "espn_public_api",
        "season": season,
        "games_per_team": per_team,
        "unique_games_written": len(unique_rows),
        "latest_game": max(row["date"] for row in unique_rows.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--teams", nargs="+", default=["tor", "mia"], help="ESPN NBA team abbreviations")
    parser.add_argument("--season", type=int, default=datetime.now(timezone.utc).year)
    parser.add_argument("--games-per-team", type=int, default=10)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.games_per_team < 1:
        parser.error("--games-per-team must be at least 1")
    print(json.dumps(refresh(args.teams, args.season, args.games_per_team, args.output), indent=2))


if __name__ == "__main__":
    main()