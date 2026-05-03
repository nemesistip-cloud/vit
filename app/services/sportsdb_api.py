"""app/services/sportsdb_api.py — TheSportsDB free-tier client for real football data.

TheSportsDB API (free key '3') — no auth required.
Endpoints used:
  eventsnextleague.php?id={league_id}   → next scheduled event per league
  eventspastleague.php?id={league_id}   → most recent finished event per league
  eventsday.php?d={YYYY-MM-DD}&s=Soccer → all soccer events on a date

Leagues supported:
  Premier League (4328), La Liga (4335), Bundesliga (4331),
  Serie A (4332), Ligue 1 (4334), Champions League (4346),
  Eredivisie (4337), Primeira Liga (4344)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

BASE = "https://www.thesportsdb.com/api/v1/json/3"

LEAGUES: Dict[str, int] = {
    "premier_league":   4328,
    "la_liga":          4335,
    "bundesliga":       4331,
    "serie_a":          4332,
    "ligue_1":          4334,
    "champions_league": 4346,
    "eredivisie":       4337,
    "primeira_liga":    4344,
}


def _map_event(ev: Dict) -> Optional[Dict]:
    """Normalise a TheSportsDB event dict to the internal match format."""
    home = (ev.get("strHomeTeam") or "").strip()
    away = (ev.get("strAwayTeam") or "").strip()
    if not home or not away:
        return None

    date_str = ev.get("dateEvent") or ""
    time_str = ev.get("strTime") or "15:00:00"
    kickoff_iso = f"{date_str}T{time_str}" if date_str else None

    try:
        kickoff_dt = datetime.fromisoformat(kickoff_iso).replace(tzinfo=timezone.utc) if kickoff_iso else None
    except ValueError:
        kickoff_dt = None

    home_score_raw = ev.get("intHomeScore")
    away_score_raw = ev.get("intAwayScore")
    home_score = int(home_score_raw) if home_score_raw not in (None, "", "null") else None
    away_score = int(away_score_raw) if away_score_raw not in (None, "", "null") else None

    status_raw = (ev.get("strStatus") or "").lower()
    if "finished" in status_raw or "ft" in status_raw:
        status = "settled"
    elif "live" in status_raw or "progress" in status_raw:
        status = "live"
    elif home_score is not None and away_score is not None:
        status = "settled"
    else:
        status = "upcoming"

    actual_outcome = None
    if status == "settled" and home_score is not None and away_score is not None:
        if home_score > away_score:
            actual_outcome = "home"
        elif away_score > home_score:
            actual_outcome = "away"
        else:
            actual_outcome = "draw"

    league_name = ev.get("strLeague") or ""
    league_slug = _league_slug(league_name)

    return {
        "external_id": str(ev.get("idEvent", "")),
        "home_team":   home,
        "away_team":   away,
        "league":      league_slug,
        "kickoff_time": kickoff_dt,
        "status":       status,
        "home_goals":   home_score,
        "away_goals":   away_score,
        "actual_outcome": actual_outcome,
        "source":      "sportsdb",
    }


def _league_slug(name: str) -> str:
    n = name.lower()
    if "premier" in n:
        return "premier_league"
    if "la liga" in n or "primera" in n and "spain" in n:
        return "la_liga"
    if "bundesliga" in n:
        return "bundesliga"
    if "serie a" in n:
        return "serie_a"
    if "ligue 1" in n:
        return "ligue_1"
    if "champions" in n:
        return "champions_league"
    if "eredivisie" in n:
        return "eredivisie"
    if "primeira" in n:
        return "primeira_liga"
    return name.lower().replace(" ", "_")


async def _fetch(path: str, timeout: int = 10) -> List[Dict]:
    """GET a TheSportsDB endpoint and return the first non-None events/results list."""
    url = f"{BASE}/{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            for key in ("events", "results"):
                evs = data.get(key)
                if evs:
                    return evs
            return []
    except Exception as exc:
        logger.debug("[sportsdb] fetch %s failed: %s", path, exc)
        return []


async def fetch_next_events() -> List[Dict]:
    """Fetch the next scheduled event for every tracked league (parallel)."""
    tasks = [_fetch(f"eventsnextleague.php?id={lid}") for lid in LEAGUES.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    events: List[Dict] = []
    for evs in results:
        if isinstance(evs, list):
            for ev in evs:
                mapped = _map_event(ev)
                if mapped:
                    events.append(mapped)
    logger.info("[sportsdb] fetch_next_events: %d events", len(events))
    return events


async def fetch_past_events() -> List[Dict]:
    """Fetch the most recently finished event for every tracked league (parallel)."""
    tasks = [_fetch(f"eventspastleague.php?id={lid}") for lid in LEAGUES.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    events: List[Dict] = []
    for evs in results:
        if isinstance(evs, list):
            for ev in evs:
                mapped = _map_event(ev)
                if mapped and mapped["status"] == "settled":
                    events.append(mapped)
    logger.info("[sportsdb] fetch_past_events: %d events", len(events))
    return events


async def fetch_events_by_date(target: date) -> List[Dict]:
    """Fetch all soccer events on a specific calendar date."""
    date_str = target.strftime("%Y-%m-%d")
    evs = await _fetch(f"eventsday.php?d={date_str}&s=Soccer")
    events = []
    for ev in evs:
        mapped = _map_event(ev)
        if mapped:
            events.append(mapped)
    return events


async def fetch_upcoming_range(days: int = 14) -> List[Dict]:
    """Fetch soccer events for the next N days via day-by-day queries."""
    today = datetime.now(timezone.utc).date()
    tasks = [fetch_events_by_date(today + timedelta(days=i)) for i in range(1, days + 1)]
    daily = await asyncio.gather(*tasks, return_exceptions=True)
    events: List[Dict] = []
    seen: set = set()
    for day_evs in daily:
        if isinstance(day_evs, list):
            for ev in day_evs:
                key = (ev["home_team"], ev["away_team"], str(ev.get("kickoff_time", "")))
                if key not in seen:
                    seen.add(key)
                    events.append(ev)
    logger.info("[sportsdb] fetch_upcoming_range(%dd): %d events", days, len(events))
    return events


async def fetch_all_real_fixtures() -> Dict[str, List[Dict]]:
    """
    Fetch a combined set of real fixtures:
      - past: recently settled matches (for model accuracy tracking)
      - upcoming: next scheduled matches per league + day-by-day for next 14 days
    Returns {"past": [...], "upcoming": [...]}
    """
    past_task = fetch_past_events()
    next_task = fetch_next_events()
    range_task = fetch_upcoming_range(days=14)

    past, nxt, rng = await asyncio.gather(past_task, next_task, range_task)

    seen_upcoming: set = set()
    upcoming: List[Dict] = []
    for ev in (nxt + rng):
        key = ev.get("external_id") or f"{ev['home_team']}|{ev['away_team']}"
        if key not in seen_upcoming:
            seen_upcoming.add(key)
            upcoming.append(ev)

    return {"past": past, "upcoming": upcoming}
