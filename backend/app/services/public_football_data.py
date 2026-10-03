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
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SOURCE_NAME = "football-data-uk"
LEAGUE_CODES = {
    "premierleague": "E0",
    "e0": "E0",
    "championship": "E1",
    "e1": "E1",
    "bundesliga": "D1",
    "d1": "D1",
    "laliga": "SP1",
    "sp1": "SP1",
    "seriea": "I1",
    "i1": "I1",
    "ligue1": "F1",
    "f1": "F1",
    "eredivisie": "N1",
    "n1": "N1",
    "primeiraliga": "P1",
    "p1": "P1",
}
LEAGUE_NAMES = {
    "E0": "premier_league",
    "E1": "championship",
    "D1": "bundesliga",
    "SP1": "la_liga",
    "I1": "serie_a",
    "F1": "ligue_1",
    "N1": "eredivisie",
    "P1": "primeira_liga",
}


def _season_urls() -> tuple[str, ...]:
    now = datetime.now(timezone.utc)
    current_season_start = now.year if now.month >= 7 else now.year - 1
    first_season_start = current_season_start - 11
    return tuple(
        f"https://football-data.co.uk/mmz4281/{start % 100:02d}{(start + 1) % 100:02d}/E0.csv"
        for start in range(first_season_start, current_season_start + 1)
    )


SEASON_URLS = _season_urls()
def _recent_season_urls(league_code: str, season_count: int = 2) -> tuple[str, ...]:
    now = datetime.now(timezone.utc)
    current_season_start = now.year if now.month >= 7 else now.year - 1
    return tuple(
        f"https://football-data.co.uk/mmz4281/{start % 100:02d}{(start + 1) % 100:02d}/{league_code}.csv"
        for start in range(current_season_start, current_season_start - season_count, -1)
    )


def _league_code(league: str) -> str | None:
    key = re.sub(r"[^a-z0-9]", "", league.lower())
    return LEAGUE_CODES.get(key)


def supports_league(league: str) -> bool:
    return _league_code(league) is not None


def _team_key(name: str) -> str:
    folded = unicodedata.normalize("NFKD", name or "")
    ascii_name = "".join(char for char in folded if not unicodedata.combining(char))
    key = re.sub(r"[^a-z0-9]", "", ascii_name.lower())
    aliases = {
        "qpr": "queensparkrangers",
        "queensparkrangersfc": "queensparkrangers",
        "westhamunitedfc": "westham",
        "1fsvmainz05": "mainz",
        "bayer04leverkusen": "bayerleverkusen",
        "ogcnice": "nice",
        "rcstrasbourgalsace": "strasbourg",
    }
    return aliases.get(key, key)


def _team_matches(candidate: str, requested: str) -> bool:
    candidate_key = _team_key(candidate)
    requested_key = _team_key(requested)
    if not candidate_key or not requested_key:
        return False
    if candidate_key == requested_key:
        return True
    if min(len(candidate_key), len(requested_key)) >= 4 and (
        candidate_key in requested_key or requested_key in candidate_key
    ):
        return True
    candidate_tokens = set(re.findall(r"[a-z0-9]+", candidate_key))
    requested_tokens = set(re.findall(r"[a-z0-9]+", requested_key))
    return len(candidate_tokens & requested_tokens) >= 2


PREMIER_LEAGUE_URLS = SEASON_URLS
GITHUB_DATASET_URL = (
    "https://raw.githubusercontent.com/AnishKhetani/premier-league-data/"
    "main/data/processed/results.csv"
)


def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _parse_iso_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
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


def _first_price(row: dict[str, str], *keys: str) -> float | None:
    for key in keys:
        price = _float(row.get(key, ""))
        if price is not None and price > 1.0:
            return price
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


def _row_to_event(
    row: dict[str, str],
    source_url: str,
    league: str = "premier_league",
) -> dict[str, Any] | None:
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
        "home_xg": _float(row.get("HxG", "")),
        "away_xg": _float(row.get("AxG", "")),
    }
    return {
        "external_id": None,
        "home_team": home,
        "away_team": away,
        "league": league,
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
        "opening_odds": {
            "home": _first_price(row, "AvgH", "B365H"),
            "draw": _first_price(row, "AvgD", "B365D"),
            "away": _first_price(row, "AvgA", "B365A"),
        },
        "closing_odds": {
            "home": _first_price(row, "AvgCH", "B365CH", "PSCH"),
            "draw": _first_price(row, "AvgCD", "B365CD", "PSCD"),
            "away": _first_price(row, "AvgCA", "B365CA", "PSCA"),
        },
    }


def _github_row_to_event(row: dict[str, str]) -> dict[str, Any] | None:
    kickoff = _parse_iso_date(row.get("date", ""))
    home = _normalise_team(row.get("home_team", ""))
    away = _normalise_team(row.get("away_team", ""))
    home_goals = _number(row.get("fthg", ""))
    away_goals = _number(row.get("ftag", ""))
    if not kickoff or not home or not away or home_goals is None or away_goals is None:
        return None

    if home_goals > away_goals:
        outcome = "home"
    elif home_goals < away_goals:
        outcome = "away"
    else:
        outcome = "draw"

    retrieved_at = datetime.now(timezone.utc).isoformat()
    return {
        "external_id": row.get("match_id") or None,
        "home_team": home,
        "away_team": away,
        "league": "premier_league",
        "sport": "football",
        "kickoff_time": kickoff,
        "status": "settled",
        "home_goals": home_goals,
        "away_goals": away_goals,
        "actual_outcome": outcome,
        "source": "github-premier-league-data",
        "source_url": GITHUB_DATASET_URL,
        "retrieved_at": retrieved_at,
        "source_metadata": {
            "provider": "github:AnishKhetani/premier-league-data",
            "source_type": "public_csv_mirror",
            "url": GITHUB_DATASET_URL,
            "upstream_provider": "football-data.co.uk",
            "retrieved_at": retrieved_at,
            "confidence": "high",
            "data_freshness": "public-dataset",
            "reliability": "public",
        },
        "statistics": {},
    }
async def fetch_historical_matches(
    before: datetime | None = None,
    teams: set[str] | None = None,
    league: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch completed rows from the relevant recent league-season CSVs."""
    cutoff = before or datetime.now(timezone.utc)
    if league:
        code = _league_code(league)
        if not code:
            logger.info("Public football CSV has no configured league mapping: %s", league)
            return []
        source_urls = _recent_season_urls(code)
        sources = [(url, code) for url in source_urls]
    else:
        source_urls = (*PREMIER_LEAGUE_URLS, GITHUB_DATASET_URL)
        sources = [(url, "E0") for url in PREMIER_LEAGUE_URLS]
        sources.append((GITHUB_DATASET_URL, "GITHUB"))
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        responses = await asyncio.gather(
            *(client.get(url) for url, _ in sources),
            return_exceptions=True,
        )

    events: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for (url, code), response in zip(sources, responses):
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
            event = (
                _github_row_to_event(row)
                if code == "GITHUB"
                else _row_to_event(row, url, LEAGUE_NAMES[code])
            )
            # The public CSV has no kickoff time. Exclude the entire cutoff
            # date so a result from later that day can never leak backward.
            if not event or event["kickoff_time"].date() >= cutoff.date():
                continue
            if teams and not any(
                _team_matches(event[side], team)
                for team in teams
                for side in ("home_team", "away_team")
            ):
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
