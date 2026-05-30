"""app/services/sportsdb_api.py — TheSportsDB free-tier client for multi-sport data.

TheSportsDB API (free key '3') — no auth required.
Endpoints used:
  eventsnextleague.php?id={league_id}       → next scheduled event per league
  eventspastleague.php?id={league_id}       → most recent finished event per league
  eventsday.php?d={YYYY-MM-DD}&s={Sport}   → all events on a date for a sport
  eventsseason.php?id={league_id}&s={yr}   → full season schedule per league

Leagues supported:
  Football: Premier League (4328), La Liga (4335), Bundesliga (4331), ...
  Basketball: NBA (4387), EuroLeague (4440)
  Tennis: ATP Tour (4934), WTA Tour (4935)
  American Football: NFL (4391)
  Baseball: MLB (4424)
  Ice Hockey: NHL (4380)
  Cricket: IPL (4484)
  MMA: UFC (4415)
  Formula 1 (4370)
  Rugby: Premiership Rugby (4305)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

import os as _os
_TSDB_KEY = _os.getenv("THESPORTSDB_API_KEY", "3")
BASE = f"https://www.thesportsdb.com/api/v1/json/{_TSDB_KEY}"

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
    "conference_league":    4480,
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

# ── Multi-sport league IDs ──────────────────────────────────────────────────
SPORT_LEAGUES: Dict[str, Dict[str, int]] = {
    "football": LEAGUES,
    "basketball": {
        "nba":              4387,
        "euroleague":       4440,
        "nba_gleague":      4388,
        "nbl_australia":    4415,
    },
    "tennis": {
        "atp_wimbledon":        4906,
        "atp_us_open":          4907,
        "atp_australian_open":  4908,
        "atp_french_open":      4909,
        "wta_tour":             4935,
    },
    "american_football": {
        "nfl":              4391,
        "ncaa_football":    4417,
    },
    "baseball": {
        "mlb":              4424,
        "npb":              4425,
    },
    "ice_hockey": {
        "nhl":              4380,
        "khl":              4383,
    },
    "cricket": {
        "ipl":              4484,
        "big_bash":         4614,
        "icc_world_cup":    4509,
    },
    "mma": {
        "ufc":              4415,
    },
    "formula1": {
        "formula_1":        4370,
    },
    "rugby": {
        "premiership_rugby": 4305,
        "super_rugby":       4306,
        "nrl":               4382,
    },
}

# Map every league key → sport type (for auto-classification)
LEAGUE_SPORT_MAP: Dict[str, str] = {
    league_key: sport
    for sport, leagues in SPORT_LEAGUES.items()
    for league_key in leagues
}

# TheSportsDB sport name for eventsday.php?s=... endpoint
TSDB_SPORT_NAMES: Dict[str, str] = {
    "football":          "Soccer",
    "basketball":        "Basketball",
    "tennis":            "Tennis",
    "american_football": "American Football",
    "baseball":          "Baseball",
    "ice_hockey":        "Ice Hockey",
    "cricket":           "Cricket",
    "mma":               "MMA",
    "formula1":          "Motorsport",
    "rugby":             "Rugby League",
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
    "conference_league":    "UEFA Conference League",
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
    # Basketball
    "nba":                  "NBA",
    "euroleague":           "EuroLeague",
    "nba_gleague":          "NBA G League",
    "nbl_australia":        "NBL (Australia)",
    # Tennis
    "atp_wimbledon":        "Wimbledon",
    "atp_us_open":          "US Open",
    "atp_australian_open":  "Australian Open",
    "atp_french_open":      "French Open",
    "wta_tour":             "WTA Tour",
    # American Football
    "nfl":                  "NFL",
    "ncaa_football":        "NCAA Football",
    # Baseball
    "mlb":                  "MLB",
    "npb":                  "NPB (Japan)",
    # Ice Hockey
    "nhl":                  "NHL",
    "khl":                  "KHL",
    # Cricket
    "ipl":                  "IPL",
    "big_bash":             "Big Bash League",
    "icc_world_cup":        "ICC World Cup",
    # MMA
    "ufc":                  "UFC",
    # Formula 1
    "formula_1":            "Formula 1",
    # Rugby
    "premiership_rugby":    "Premiership Rugby",
    "super_rugby":          "Super Rugby",
    "nrl":                  "NRL",
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
    """Fetch the next scheduled events for every tracked league — SEQUENTIALLY.

    Uses eventsnextleague.php which specifically returns upcoming (future) fixtures.
    Sequential with 2s delays to respect the free-tier rate limit.
    """
    events: List[Dict] = []
    league_items = list(LEAGUES.items())
    for i, (slug, lid) in enumerate(league_items):
        evs = await _fetch(f"eventsnextleague.php?id={lid}")
        for ev in evs:
            mapped = _map_event(ev)
            if mapped:
                if not mapped.get("league") or mapped["league"] == "unknown":
                    mapped["league"] = slug
                events.append(mapped)
        if i < len(league_items) - 1:
            await asyncio.sleep(2.0)
    logger.info("[sportsdb] fetch_next_events: %d events across %d leagues", len(events), len(LEAGUES))
    return events


async def fetch_past_events() -> List[Dict]:
    """Fetch the most recently finished event for every tracked league — SEQUENTIALLY."""
    events: List[Dict] = []
    league_items = list(LEAGUES.items())
    for i, (slug, lid) in enumerate(league_items):
        evs = await _fetch(f"eventspastleague.php?id={lid}")
        for ev in evs:
            mapped = _map_event(ev)
            if mapped and mapped["status"] == "settled":
                if not mapped.get("league") or mapped["league"] == "unknown":
                    mapped["league"] = slug
                events.append(mapped)
        if i < len(league_items) - 1:
            await asyncio.sleep(2.0)
    logger.info("[sportsdb] fetch_past_events: %d events across %d leagues", len(events), len(LEAGUES))
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

    # Batch in groups of 3 concurrent requests — free-tier is rate-limited
    batch_size = 3
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
        # 2-second pause between each batch to respect free-tier rate limits
        if start + batch_size < len(dates):
            await asyncio.sleep(2.0)

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
    """Fetch the full current-season schedule for all tracked leagues SEQUENTIALLY.

    Sequential (not parallel) to avoid 429 rate limits on the free API tier.
    Filters to only upcoming fixtures within `days_ahead` days.
    Returns deduplicated upcoming events.
    """
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days_ahead)

    events: List[Dict] = []
    seen: set = set()

    league_items = list(LEAGUES.items())
    for i, (slug, lid) in enumerate(league_items):
        try:
            league_evs = await _fetch_season_for_league(slug, lid)
        except Exception as exc:
            logger.warning("[sportsdb] season fetch error for %s: %s", slug, exc)
            league_evs = []

        for ev in league_evs:
            ko = ev.get("kickoff_time")
            if not ko:
                continue
            if ev.get("status") == "settled":
                continue
            ko_utc = ko if ko.tzinfo else ko.replace(tzinfo=timezone.utc)
            if ko_utc < now or ko_utc > cutoff:
                continue
            key = ev.get("external_id") or f"{ev['home_team']}|{ev['away_team']}|{ko}"
            if key not in seen:
                seen.add(key)
                events.append(ev)

        # Throttle between each league to stay within free-tier rate limits
        if i < len(league_items) - 1:
            await asyncio.sleep(1.5)

    logger.info(
        "[sportsdb] fetch_season_fixtures(days_ahead=%d): %d upcoming fixtures across %d leagues",
        days_ahead, len(events), len(LEAGUES),
    )
    return events


async def fetch_all_real_fixtures() -> Dict[str, List[Dict]]:
    """
    Fetch a combined set of real fixtures (sequential, rate-limit safe):
      - past: recently settled matches per league (eventspastleague)
      - upcoming: next scheduled matches per league (eventsnextleague)
    Both are fetched sequentially with 2s delays between each league.
    Returns {"past": [...], "upcoming": [...]}
    """
    # Past events first (sequential)
    past = await fetch_past_events()
    # Then upcoming (sequential, reuses same throttling)
    upcoming = await fetch_next_events()

    logger.info(
        "[sportsdb] fetch_all_real_fixtures: %d past + %d upcoming",
        len(past), len(upcoming),
    )
    return {"past": past, "upcoming": upcoming}


async def fetch_historical_range(days_back: int = 180) -> List[Dict]:
    """
    Fetch real historical match results for the past N days (day by day).
    Returns only settled matches with actual_outcome set.
    Used for: ML training data, CLV backfill, model accuracy tracking.
    """
    today = datetime.now(timezone.utc).date()
    dates = [today - timedelta(days=i) for i in range(1, days_back + 1)]

    # Fetch in chunks of 2 days concurrently — free-tier allows ~1 req/sec
    # Larger batches cause 429s. Increase sleep between chunks for safety.
    chunk_size = 2
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
        # 3-second pause between each 2-day chunk to stay within free-tier limits
        if chunk_start + chunk_size < len(dates):
            await asyncio.sleep(3.0)

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

    # --- Primary: full season calendar (best coverage for multi-week windows) ---
    # fetch_season_fixtures calls eventsseason.php per league, which returns the
    # complete schedule for the current season, filtered to the days_ahead window.
    # This is the only way to get 200-500 upcoming matches reliably.
    season_events = await fetch_season_fixtures(days_ahead=days_ahead)

    # --- Supplement: next-events per league ---
    # eventsnextleague.php catches near-term fixtures not yet in the season
    # calendar (rescheduled games, cup matches) and is fast.
    next_events = await fetch_next_events()

    logger.info(
        "[sportsdb] sync_upcoming: %d season + %d next_events before dedup",
        len(season_events), len(next_events),
    )

    # Merge, deduplicated by external_id then by home/away/date
    seen_keys: set = set()
    all_events: List[Dict] = []
    for ev in season_events + next_events:
        key = ev.get("external_id") or f"{ev['home_team']}|{ev['away_team']}|{ev.get('kickoff_time', '')}"
        if key not in seen_keys:
            seen_keys.add(key)
            all_events.append(ev)
    logger.info(
        "[sportsdb] sync_upcoming: %d events to process",
        len(all_events),
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


async def sync_fixture_results(db, days_back: int = 7) -> Dict:
    """
    Finalize Phase 3a: Result Settlement.
    Poll for match results and update Match.actual_outcome.
    """
    return await sync_and_insert_historical(db, days_back=days_back)
