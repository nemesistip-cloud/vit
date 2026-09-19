"""Public Football-Data.co.uk CSV provider.

The source publishes structured historical results and match statistics for
English competitions without requiring an API key. This adapter keeps the
source URL and retrieval metadata with each normalized event so callers can
persist or audit provenance without manufacturing missing values.
"""
from __future__ import annotations

import asyncio
import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SOURCE_NAME = "football-data-uk"
SEASON_URLS = (
    "https://football-data.co.uk/mmz4281/2627/E0.csv",
    "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    "https://www.football-data.co.uk/mmz4281/2425/E0.csv",
)
PREMIER_LEAGUE_URLS = SEASON_URLS


def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _number(value: str) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _float(value: str) -> float | None:
    try:
        cleaned = str(value).strip().replace(",", "")
        return float(cleaned) if cleaned not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _normalise_team(name: str) -> str:
    aliases = {
        "Man United": "Manchester United FC",
        "Man City": "Manchester City FC",
        "Nott'm Forest": "Nottingham Forest FC",
        "Newcastle": "Newcastle United FC",
        "Wolves": "Wolverhampton Wanderers FC",
        "Leeds": "Leeds United FC",
        "Brighton": "Brighton & Hove Albion FC",
        "Tottenham": "Tottenham Hotspur FC",
        "Aston Villa": "Aston Villa FC",
    }
    return aliases.get(name.strip(), name.strip())


def _row_to_event(row: dict[str, str], source_url: str) -> dict[str, Any] | None:
    kickoff = _parse_date(row.get("Date", ""))
    home = _normalise_team(row.get("HomeTeam", ""))
    away = _normalise_team(row.get("AwayTeam", ""))
    home_goals = _number(row.get("FTHG", ""))
    away_goals = _number(row.get("FTAG", ""))
    if not kickoff or not home or not away or home_goals is None or away_goals is None:
        return None

    if home_goals > away_goals:
        outcome = "home"
    elif home_goals < away_goals:
        outcome = "away"
    else:
        outcome = "draw"

    retrieved_at = datetime.now(timezone.utc).isoformat()
    stats = {
        "home_shots": _number(row.get("HS", "")),
        "away_shots": _number(row.get("AS", "")),
        "home_shots_on_target": _number(row.get("HST", "")),
        "away_shots_on_target": _number(row.get("AST", "")),
        "home_corners": _number(row.get("HC", "")),
        "away_corners": _number(row.get("AC", "")),
        "home_fouls": _number(row.get("HF", "")),
        "away_fouls": _number(row.get("AF", "")),
        "home_yellow_cards": _number(row.get("HY", "")),
        "away_yellow_cards": _number(row.get("AY", "")),
        "home_red_cards": _number(row.get("HR", "")),
        "away_red_cards": _number(row.get("AR", "")),
        "home_xg": _float(row.get("HxG", "")) or _float(row.get("HxG", "")),
        "away_xg": _float(row.get("AxG", "")) or _float(row.get("AxG", "")),
    }
    return {
        "external_id": None,
        "home_team": home,
        "away_team": away,
        "league": "premier_league",
        "sport": "football",
        "kickoff_time": kickoff,
        "status": "settled",
        "home_goals": home_goals,
        "away_goals": away_goals,
        "actual_outcome": outcome,
        "source": SOURCE_NAME,
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "source_metadata": {
            "provider": "football-data.co.uk",
            "source_type": "public_csv",
            "url": source_url,
            "retrieved_at": retrieved_at,
            "confidence": "high",
            "data_freshness": "public-season-csv",
            "reliability": "public",
        },
        "statistics": stats,
    }


async def fetch_historical_matches(before: datetime | None = None) -> list[dict[str, Any]]:
    """Fetch completed Premier League rows from public season CSVs."""
    cutoff = before or datetime.now(timezone.utc)
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        responses = await asyncio.gather(
            *(client.get(url) for url in PREMIER_LEAGUE_URLS),
            return_exceptions=True,
        )

    events: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for url, response in zip(PREMIER_LEAGUE_URLS, responses):
        if isinstance(response, Exception):
            logger.warning("Public football CSV unavailable source=%s error=%s", url, type(response).__name__)
            continue
        if response.status_code != 200:
            logger.warning(
                "Public football CSV rejected source=%s status=%s",
                url,
                response.status_code,
            )
            continue
        try:
            csv_text = response.content.decode("utf-8-sig")
        except UnicodeDecodeError:
            csv_text = response.content.decode("latin-1")
        for row in csv.DictReader(io.StringIO(csv_text)):
            event = _row_to_event(row, url)
            # The public CSV has no kickoff time. Exclude the entire cutoff
            # date so a result from later that day can never leak backward.
            if not event or event["kickoff_time"].date() >= cutoff.date():
                continue
            key = (
                event["kickoff_time"].date().isoformat(),
                event["home_team"].lower(),
                event["away_team"].lower(),
            )
            if key not in seen:
                seen.add(key)
                events.append(event)
    events.sort(key=lambda item: item["kickoff_time"])
    logger.info("Public football CSV history fetched events=%d sources=%d", len(events), len(PREMIER_LEAGUE_URLS))
    return events
