"""app/services/sportsdb_api.py — TheSportsDB free-tier client for real football data.

TheSportsDB API (free key '3') — no auth required.
Endpoints used:
  eventsnextleague.php?id={league_id}      → next scheduled event per league
  eventspastleague.php?id={league_id}      → most recent finished event per league
  eventsday.php?d={YYYY-MM-DD}&s=Soccer    → all soccer events on a date
  eventsseason.php?id={league_id}&s={yr}   → full season schedule per league  ← NEW

Leagues supported (extended):
  Premier League (4328), La Liga (4335), Bundesliga (4331),
  Serie A (4332), Ligue 1 (4334), Champions League (4346),
  Europa League (4375), Eredivisie (4337), Primeira Liga (4344),
  Championship (4329), Scottish Premiership (4330),
  Belgian Pro League (4397), MLS (4346 alt / 4399),
  Liga MX (4350), Brasileirão (4351), Argentine Primera (4406),
  Süper Lig (4347), Ekstraklasa (4422), Jupiler (4397)
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
    # Top 5 European leagues
    "premier_league":       4328,
    "la_liga":              4335,
    "bundesliga":           4331,
    "serie_a":              4332,
    "ligue_1":              4334,
    # European club competitions
    "champions_league":     4346,
    "europa_league":        4375,
    # Other top European leagues
    "eredivisie":           4337,
    "primeira_liga":        4344,
    "championship":         4329,
    "scottish_premiership": 4330,
    "belgian_pro_league":   4397,
    "super_lig":            4347,
    "ekstraklasa":          4422,
    # Americas
    "mls":                  4399,
    "liga_mx":              4350,
    "brasileirao":          4351,
    "argentine_primera":    4406,
}

# Human-readable names used for league slug → display name mapping
LEAGUE_DISPLAY: Dict[str, str] = {
    "premier_league":       "Premier League",
    "la_liga":              "La Liga",
    "bundesliga":           "Bundesliga",
    "serie_a":              "Serie A",
    "ligue_1":              "Ligue 1",
    "champions_league":     "Champions League",
    "europa_league":        "Europa League",
    "eredivisie":           "Eredivisie",
    "primeira_liga":        "Primeira Liga",
    "championship":         "Championship",
    "scottish_premiership": "Scottish Premiership",
    "belgian_pro_league":   "Belgian Pro League",
    "super_lig":            "Süper Lig",
    "ekstraklasa":          "Ekstraklasa",
    "mls":                  "MLS",
    "liga_mx":              "Liga MX",
    "brasileirao":          "Brasileirão",
    "argentine_primera":    "Argentine Primera División",
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
    if "premier league" in n and "scotland" not in n:
        return "premier_league"
    if "la liga" in n or ("primera" in n and "spain" in n):
        return "la_liga"
    if "bundesliga" in n:
        return "bundesliga"
    if "serie a" in n and "brazil" not in n:
        return "serie_a"
    if "ligue 1" in n:
        return "ligue_1"
    if "champions league" in n or "uefa champions" in n:
        return "champions_league"
    if "europa league" in n or "uefa europa" in n:
        return "europa_league"
    if "eredivisie" in n:
        return "eredivisie"
    if "primeira liga" in n or "portuguese" in n:
        return "primeira_liga"
    if "championship" in n and "scotland" not in n:
        return "championship"
    if "scottish" in n or ("premier" in n and "scotland" in n):
        return "scottish_premiership"
    if "belgian" in n or "jupiler" in n or "pro league" in n:
        return "belgian_pro_league"
    if "süper lig" in n or "super lig" in n or "turkish" in n:
        return "super_lig"
    if "ekstraklasa" in n or "polish" in n:
        return "ekstraklasa"
    if "major league soccer" in n or " mls" in n:
        return "mls"
    if "liga mx" in n or "mexican" in n:
        return "liga_mx"
    if "brasileirão" in n or "brasileiro" in n or "brazil" in n:
        return "brasileirao"
    if "argentine" in n or "primera división" in n:
        return "argentine_primera"
    return name.lower().replace(" ", "_")


async def _fetch(path: str, timeout: int = 15) -> List[Dict]:
    """GET a TheSportsDB endpoint and return the first non-None events/results list.

    Returns [] immediately on rate-limit (429) or any error — callers should
    handle absence of data gracefully. The background sync loop retries naturally
    every 3 hours, so inline retries are not needed and would block startup.
    """
    url = f"{BASE}/{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url)
            if r.status_code == 429:
                retry_after = r.headers.get("retry-after", "?")
                logger.warning(
                    "[sportsdb] rate-limited (429) on %s (retry-after=%s) — skipping",
                    path, retry_after,
                )
                return []
            r.raise_for_status()
            data = r.json()
            for key in ("events", "results"):
                evs = data.get(key)
                if evs:
                    return evs
            return []
    except httpx.TimeoutException:
        logger.debug("[sportsdb] timeout on %s", path)
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


async def fetch_upcoming_range(days: int = 60) -> List[Dict]:
    """Fetch soccer events for the next N days via day-by-day queries.

    Runs date requests in batches of 10 to avoid hammering the free API.
    """
    today = datetime.now(timezone.utc).date()
    dates = [today + timedelta(days=i) for i in range(1, days + 1)]

    # Batch in groups of 10 concurrent requests
    batch_size = 10
    events: List[Dict] = []
    seen: set = set()

    for start in range(0, len(dates), batch_size):
        batch = dates[start: start + batch_size]
        tasks = [fetch_events_by_date(d) for d in batch]
        daily = await asyncio.gather(*tasks, return_exceptions=True)
        for day_evs in daily:
            if isinstance(day_evs, list):
                for ev in day_evs:
                    key = (ev["home_team"], ev["away_team"], str(ev.get("kickoff_time", "")))
                    if key not in seen:
                        seen.add(key)
                        events.append(ev)
        # Small pause between batches to be polite to the free API
        if start + batch_size < len(dates):
            await asyncio.sleep(0.5)

    logger.info("[sportsdb] fetch_upcoming_range(%dd): %d events", days, len(events))
    return events


def _current_seasons() -> List[str]:
    """Return the current and upcoming season strings to try (e.g. '2025-2026', '2025')."""
    now = datetime.now(timezone.utc)
    year = now.year
    # Football seasons can be single-year (Americas) or split-year (Europe)
    return [
        f"{year}-{year + 1}",   # e.g. 2025-2026 (European split season)
        f"{year - 1}-{year}",   # e.g. 2024-2025 (still running)
        str(year),              # e.g. 2025 (Americas / single-year season)
    ]


async def _fetch_season_for_league(league_slug: str, league_id: int) -> List[Dict]:
    """Fetch the full season schedule for one league, trying multiple season strings."""
    seasons = _current_seasons()
    for season in seasons:
        evs = await _fetch(f"eventsseason.php?id={league_id}&s={season}", timeout=20)
        if evs:
            mapped = []
            for ev in evs:
                m = _map_event(ev)
                if m:
                    # Ensure league slug is set correctly
                    if not m.get("league") or m["league"] == "unknown":
                        m["league"] = league_slug
                    mapped.append(m)
            if mapped:
                logger.info(
                    "[sportsdb] season %s %s: %d fixtures", season, league_slug, len(mapped)
                )
                return mapped
    return []


async def fetch_season_fixtures(days_ahead: int = 90) -> List[Dict]:
    """Fetch the full current-season schedule for all tracked leagues in parallel.

    Filters to only upcoming fixtures within `days_ahead` days.
    This is the most efficient way to get a large batch of future fixtures.
    Returns deduplicated upcoming events.
    """
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days_ahead)

    tasks = [
        _fetch_season_for_league(slug, lid)
        for slug, lid in LEAGUES.items()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    events: List[Dict] = []
    seen: set = set()

    for league_evs in results:
        if not isinstance(league_evs, list):
            continue
        for ev in league_evs:
            ko = ev.get("kickoff_time")
            if not ko:
                continue
            # Keep only upcoming fixtures within the window
            if ev.get("status") == "settled":
                continue
            ko_utc = ko if ko.tzinfo else ko.replace(tzinfo=timezone.utc)
            if ko_utc < now or ko_utc > cutoff:
                continue
            key = ev.get("external_id") or f"{ev['home_team']}|{ev['away_team']}|{ko}"
            if key not in seen:
                seen.add(key)
                events.append(ev)

    logger.info(
        "[sportsdb] fetch_season_fixtures(days_ahead=%d): %d upcoming fixtures across %d leagues",
        days_ahead, len(events), len(LEAGUES),
    )
    return events


async def fetch_all_real_fixtures() -> Dict[str, List[Dict]]:
    """
    Fetch a combined set of real fixtures:
      - past: recently settled matches (for model accuracy tracking)
      - upcoming: season schedule + next events per league + day-by-day for next 14 days
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


async def fetch_historical_range(days_back: int = 180) -> List[Dict]:
    """
    Fetch real historical match results for the past N days (day by day).
    Returns only settled matches with actual_outcome set.
    Used for: ML training data, CLV backfill, model accuracy tracking.
    """
    today = datetime.now(timezone.utc).date()
    dates = [today - timedelta(days=i) for i in range(1, days_back + 1)]

    # Fetch in chunks of 5 days concurrently to respect free-tier rate limits
    chunk_size = 5
    all_events: List[Dict] = []
    seen: set = set()

    for chunk_start in range(0, len(dates), chunk_size):
        chunk = dates[chunk_start: chunk_start + chunk_size]
        tasks = [fetch_events_by_date(d) for d in chunk]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for day_evs in results:
            if not isinstance(day_evs, list):
                continue
            for ev in day_evs:
                if ev.get("status") != "settled" or not ev.get("actual_outcome"):
                    continue
                key = ev.get("external_id") or f"{ev['home_team']}|{ev['away_team']}|{ev.get('kickoff_time', '')}"
                if key not in seen:
                    seen.add(key)
                    all_events.append(ev)
        # Slightly longer pause to stay within free-tier rate limits
        await asyncio.sleep(0.8)

    logger.info("[sportsdb] fetch_historical_range(%dd): %d settled events", days_back, len(all_events))
    return all_events


async def backfill_historical_matches(db, months: int = 12) -> Dict:
    """
    Fetch last N months of results from TheSportsDB for all tracked leagues.
    Insert as Match rows with source='sportsdb'. Skip duplicates via fingerprint.
    Set actual_outcome for completed matches.
    Returns {inserted, updated, skipped, total_fetched}.
    """
    days_back = months * 30
    return await sync_and_insert_historical(db, days_back=days_back)


async def sync_upcoming_fixtures(db, days_ahead: int = 60) -> Dict:
    """
    Fetch upcoming fixtures for the next N days and upsert as Match rows.

    Strategy (in order):
    1. Season schedule fetch — pulls the full current-season calendar for all
       leagues in one round-trip per league. Best coverage for far-future dates.
    2. Day-by-day range scan — catches matches not yet in the season schedule
       (e.g. cup replays, rescheduled games).

    Returns {inserted, updated, skipped, total_fetched}.
    """
    from sqlalchemy import select
    from app.db.models import Match

    # --- Phase 1: season schedule ---
    season_events = await fetch_season_fixtures(days_ahead=days_ahead)

    # --- Phase 2: day-by-day range (up to 30 days) ---
    range_days = min(days_ahead, 30)
    range_events = await fetch_upcoming_range(days=range_days)

    # Merge, deduplicated by external_id then by home/away/date
    seen_keys: set = set()
    all_events: List[Dict] = []
    for ev in season_events + range_events:
        key = ev.get("external_id") or f"{ev['home_team']}|{ev['away_team']}|{ev.get('kickoff_time', '')}"
        if key not in seen_keys:
            seen_keys.add(key)
            all_events.append(ev)

    logger.info(
        "[sportsdb] sync_upcoming: %d season + %d range = %d unique events to process",
        len(season_events), len(range_events), len(all_events),
    )

    inserted = 0
    updated = 0
    skipped = 0

    for ev in all_events:
        home = ev["home_team"]
        away = ev["away_team"]
        kickoff = ev.get("kickoff_time")
        ext_id = ev.get("external_id") or None
        league = ev.get("league", "unknown")

        if not kickoff:
            skipped += 1
            continue

        ko_naive = kickoff.replace(tzinfo=None) if kickoff and kickoff.tzinfo else kickoff
        date_str = ko_naive.strftime("%Y-%m-%d") if ko_naive else "unknown"
        fingerprint = f"{date_str}::{home.lower()}::{away.lower()}::{league}"

        try:
            existing = None
            if ext_id:
                res = await db.execute(select(Match).where(Match.external_id == ext_id))
                existing = res.scalar_one_or_none()
            if not existing:
                res = await db.execute(select(Match).where(Match.fingerprint == fingerprint))
                existing = res.scalar_one_or_none()

            if existing:
                # Backfill external_id if missing
                changed = False
                if ext_id and not existing.external_id:
                    existing.external_id = ext_id
                    changed = True
                # Update kickoff if it changed (rescheduled match)
                if ko_naive and existing.kickoff_time and abs(
                    (existing.kickoff_time - ko_naive).total_seconds()
                ) > 300:
                    existing.kickoff_time = ko_naive
                    changed = True
                if changed:
                    await db.commit()
                    updated += 1
                else:
                    skipped += 1
            else:
                match = Match(
                    external_id=ext_id,
                    home_team=home,
                    away_team=away,
                    league=league,
                    kickoff_time=ko_naive,
                    status="upcoming",
                    source="sportsdb",
                    fingerprint=fingerprint,
                )
                db.add(match)
                await db.commit()
                inserted += 1
        except Exception as exc:
            logger.debug("[sportsdb] sync_upcoming insert error for %s vs %s: %s", home, away, exc)
            await db.rollback()
            skipped += 1

    logger.info(
        "[sportsdb] sync_upcoming_fixtures done: inserted=%d updated=%d skipped=%d total=%d",
        inserted, updated, skipped, len(all_events),
    )
    return {"inserted": inserted, "updated": updated, "skipped": skipped, "total_fetched": len(all_events)}


async def sync_and_insert_historical(db, days_back: int = 180) -> Dict:
    """
    Fetch historical matches from TheSportsDB and upsert them into the DB.
    Returns stats: {inserted, updated, skipped, total_fetched}
    """
    from sqlalchemy import select
    from app.db.models import Match

    events = await fetch_historical_range(days_back=days_back)

    inserted = 0
    updated = 0
    skipped = 0

    for ev in events:
        ext_id = ev.get("external_id") or ""
        home = ev["home_team"]
        away = ev["away_team"]
        kickoff = ev.get("kickoff_time")

        if not kickoff:
            skipped += 1
            continue

        date_str = kickoff.strftime("%Y-%m-%d") if kickoff else "unknown"
        fingerprint = f"{date_str}::{home.lower()}::{away.lower()}::{ev.get('league', '')}"

        try:
            existing = None
            if ext_id:
                res = await db.execute(select(Match).where(Match.external_id == ext_id))
                existing = res.scalar_one_or_none()
            if not existing:
                res = await db.execute(select(Match).where(Match.fingerprint == fingerprint))
                existing = res.scalar_one_or_none()

            if existing:
                changed = False
                if ev.get("actual_outcome") and not existing.actual_outcome:
                    existing.actual_outcome = ev["actual_outcome"]
                    existing.home_goals = ev.get("home_goals")
                    existing.away_goals = ev.get("away_goals")
                    existing.status = "settled"
                    changed = True
                if changed:
                    await db.commit()
                    updated += 1
                else:
                    skipped += 1
            else:
                match = Match(
                    external_id=ext_id or None,
                    home_team=home,
                    away_team=away,
                    league=ev.get("league", "unknown"),
                    kickoff_time=kickoff,
                    status=ev.get("status", "settled"),
                    home_goals=ev.get("home_goals"),
                    away_goals=ev.get("away_goals"),
                    actual_outcome=ev.get("actual_outcome"),
                    source="sportsdb",
                    fingerprint=fingerprint,
                )
                db.add(match)
                await db.commit()
                inserted += 1
        except Exception as exc:
            logger.debug("[sportsdb] insert error for %s vs %s: %s", home, away, exc)
            await db.rollback()
            skipped += 1

    logger.info(
        "[sportsdb] historical sync done: inserted=%d updated=%d skipped=%d total=%d",
        inserted, updated, skipped, len(events),
    )
    return {"inserted": inserted, "updated": updated, "skipped": skipped, "total_fetched": len(events)}
