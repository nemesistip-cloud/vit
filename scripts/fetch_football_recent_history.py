#!/usr/bin/env python3
"""Refresh public Premier League results used by prediction features."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.services.public_football_data import fetch_historical_matches

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data/sports/football/premier_league_matches.csv"
FIELDS = (
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "date",
    "league",
    "source",
    "source_url",
    "external_id",
)


async def refresh(output: Path) -> dict:
    events = await fetch_historical_matches(before=datetime.now(timezone.utc))
    completed = [
        event for event in events
        if event.get("status") == "settled"
        and event.get("home_goals") is not None
        and event.get("away_goals") is not None
        and event.get("kickoff_time") is not None
    ]
    if not completed:
        raise RuntimeError("Public football-data sources returned no completed scored matches")

    unique: dict[tuple[str, str, str], dict] = {}
    for event in completed:
        kickoff = event["kickoff_time"]
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        key = (
            kickoff.date().isoformat(),
            event["home_team"].lower(),
            event["away_team"].lower(),
        )
        unique.setdefault(key, {
            "home_team": event["home_team"],
            "away_team": event["away_team"],
            "home_score": event["home_goals"],
            "away_score": event["away_goals"],
            "date": kickoff.astimezone(timezone.utc).isoformat(),
            "league": event.get("league") or "premier_league",
            "source": event.get("source") or "football-data-uk",
            "source_url": event.get("source_url") or "",
            "external_id": event.get("external_id") or "",
        })

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
                unique.values(), key=lambda row: row["date"], reverse=True
            ))
        os.replace(temporary_path, output)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()

    return {
        "output": str(output),
        "records_written": len(unique),
        "sources": sorted({row["source"] for row in unique.values()}),
        "latest_result": max(row["date"] for row in unique.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(refresh(args.output)), indent=2))


if __name__ == "__main__":
    main()
