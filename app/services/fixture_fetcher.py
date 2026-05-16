"""app/services/fixture_fetcher.py — Multi-source fixture fetching with automatic fallback chain.

Priority order:
  1. TheSportsDB   (free key='3', no auth required) — always first, broadest free coverage
  2. football-data.org (FOOTBALL_DATA_API_KEY)      — high quality, rate-limited
  3. OpenLigaDB    (free, no auth)                  — German/Austrian leagues
  4. API-Football  (API_FOOTBALL_KEY via RapidAPI)  — wide coverage if key available

All sources normalise to the internal match dict:
  {home_team, away_team, league, kickoff_time (datetime|None),
   external_id (str|None), status, source (str)}

Usage:
    from app.services.fixture_fetcher import fetch_upcoming_multi_source
    events = await fetch_upcoming_multi_source(days_ahead=14)
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ── OpenLigaDB league identifiers (free, no auth) ────────────────────────────
# https://api.openligadb.de/getmatchdata/{leagueShortcut}/{leagueSeason}
_OPENLIGA_LEAGUES: Dict[str, Dict[str, Any]] = {
    "bundesliga":    {"shortcut": "bl1",  "name": "Bundesliga"},
    "bundesliga_2":  {"shortcut": "bl2",  "name": "2. Bundesliga"},
    "dfb_pokal":     {"shortcut": "dfb",  "name": "DFB Pokal"},
    "austria_bl":    {"shortcut": "oefbl", "name": "Austrian Bundesliga"},
}

# TheSportsDB league IDs — same as sportsdb_api.py
_SPORTSDB_LEAGUES: Dict[str, int] = {
    "premier_league":   4328,
    "la_liga":          4335,
    "bundesliga":       4331,
    "serie_a":          4332,
    "ligue_1":          4334,
    "champions_league": 4346,
    "eredivisie":       4337,
    "primeira_liga":    4344,
    "scottish_premiership": 4330,
    "mls":              4346,
}

_OPENLIGA_BASE = "https://api.openligadb.de"
_SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"
_FDATA_BASE    = "https://api.football-data.org/v4"
_API_FOOTBALL_BASE = "https://v3.football.api-sports.io"

_TIMEOUT = 10  # seconds per request


# ── Internal normalisation helpers ────────────────────────────────────────────

def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s[:19], fmt[:len(s[:19])])
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _league_slug(raw: str) -> str:
    raw = raw.lower().strip()
    mapping = {
        "premier league": "premier_league",
        "english premier league": "premier_league",
        "la liga": "la_liga",
        "primera division": "la_liga",
        "bundesliga": "bundesliga",
        "bundesliga 1": "bundesliga",
        "serie a": "serie_a",
        "ligue 1": "ligue_1",
        "champions league": "champions_league",
        "uefa champions league": "champions_league",
        "eredivisie": "eredivisie",
        "primeira liga": "primeira_liga",
        "scottish premiership": "scottish_premiership",
        "mls": "mls",
        "2. bundesliga": "bundesliga_2",
        "dfb pokal": "dfb_pokal",
    }
    return mapping.get(raw, raw.replace(" ", "_"))


# ── Source 1: TheSportsDB (free, no auth) ─────────────────────────────────────

async def _fetch_sportsdb_range(days_ahead: int = 14) -> List[Dict]:
    """Fetch upcoming fixtures from TheSportsDB free API."""
    today = date.today()
    all_events: List[Dict] = []
    seen_ids: set = set()

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        # 1a. Next events per league
        tasks = [
            client.get(f"{_SPORTSDB_BASE}/eventsnextleague.php?id={lid}")
            for lid in _SPORTSDB_LEAGUES.values()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                continue
            try:
                events = r.json().get("events") or []
                for ev in events:
                    _add_sportsdb_event(ev, all_events, seen_ids)
            except Exception:
                pass

        # 1b. Day-by-day for first 7 days
        date_tasks = [
            client.get(f"{_SPORTSDB_BASE}/eventsday.php?d={(today + timedelta(days=i)).strftime('%Y-%m-%d')}&s=Soccer")
            for i in range(1, min(days_ahead, 8))
        ]
        day_results = await asyncio.gather(*date_tasks, return_exceptions=True)
        for r in day_results:
            if isinstance(r, Exception):
                continue
            try:
                events = r.json().get("events") or []
                for ev in events:
                    _add_sportsdb_event(ev, all_events, seen_ids)
            except Exception:
                pass

    logger.info("[fixture-fetcher] TheSportsDB: %d events", len(all_events))
    return all_events


def _add_sportsdb_event(ev: Dict, all_events: List[Dict], seen: set) -> None:
    eid = str(ev.get("idEvent") or "")
    home = (ev.get("strHomeTeam") or "").strip()
    away = (ev.get("strAwayTeam") or "").strip()
    if not home or not away or eid in seen:
        return
    date_str = ev.get("dateEvent") or ""
    time_str = ev.get("strTime") or "15:00:00"
    kickoff_raw = f"{date_str}T{time_str}" if date_str else None
    kickoff = _parse_dt(kickoff_raw)
    # Only keep upcoming
    if kickoff and kickoff < datetime.now(timezone.utc):
        return
    status_raw = (ev.get("strStatus") or "").lower()
    if "finished" in status_raw or "ft" in status_raw:
        return
    seen.add(eid)
    all_events.append({
        "home_team":   home,
        "away_team":   away,
        "league":      _league_slug(ev.get("strLeague") or ""),
        "kickoff_time": kickoff,
        "external_id": eid or None,
        "status":      "upcoming",
        "source":      "sportsdb",
    })


# ── Source 2: football-data.org (rate-limited) ────────────────────────────────

_FDATA_COMPETITIONS = {
    "premier_league":       "PL",
    "serie_a":              "SA",
    "la_liga":              "PD",
    "bundesliga":           "BL1",
    "ligue_1":              "FL1",
    "championship":         "ELC",
    "eredivisie":           "DED",
    "primeira_liga":        "PPL",
    "scottish_premiership": "SPL",
    "champions_league":     "CL",
    "europa_league":        "EL",
}


async def _fetch_football_data(days_ahead: int = 14) -> List[Dict]:
    """Fetch from football-data.org. Returns empty list if rate-limited or key missing."""
    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()
    if not api_key:
        logger.debug("[fixture-fetcher] FOOTBALL_DATA_API_KEY not set — skipping")
        return []

    now = datetime.now(timezone.utc)
    date_from = now.strftime("%Y-%m-%d")
    date_to   = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    events: List[Dict] = []
    rate_limited = False

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for league, code in _FDATA_COMPETITIONS.items():
            if rate_limited:
                break
            try:
                r = await client.get(
                    f"{_FDATA_BASE}/competitions/{code}/matches",
                    headers={"X-Auth-Token": api_key},
                    params={"status": "SCHEDULED", "dateFrom": date_from, "dateTo": date_to},
                    timeout=8,
                )
                if r.status_code == 200:
                    for m in r.json().get("matches", []):
                        try:
                            events.append({
                                "home_team":    m["homeTeam"]["name"],
                                "away_team":    m["awayTeam"]["name"],
                                "league":       league,
                                "kickoff_time": _parse_dt(m.get("utcDate")),
                                "external_id":  f"fdata-{m.get('id', '')}",
                                "status":       "upcoming",
                                "source":       "football-data",
                            })
                        except (KeyError, TypeError):
                            pass
                elif r.status_code == 429:
                    logger.warning("[fixture-fetcher] football-data.org rate-limited — switching to fallback sources")
                    rate_limited = True
                elif r.status_code in (401, 403):
                    logger.warning("[fixture-fetcher] football-data.org auth error %s — key may be invalid", r.status_code)
                    break
            except httpx.TimeoutException:
                logger.debug("[fixture-fetcher] football-data.org timeout for %s", league)
            except Exception as exc:
                logger.debug("[fixture-fetcher] football-data.org error for %s: %s", league, exc)

    logger.info("[fixture-fetcher] football-data.org: %d events (rate_limited=%s)", len(events), rate_limited)
    return events


# ── Source 3: OpenLigaDB (free, no auth) ──────────────────────────────────────

async def _fetch_openligadb(days_ahead: int = 14) -> List[Dict]:
    """Fetch from OpenLigaDB (German football, free, no auth)."""
    season = datetime.now().year
    events: List[Dict] = []

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        tasks = []
        league_keys = []
        for key, info in _OPENLIGA_LEAGUES.items():
            shortcut = info["shortcut"]
            tasks.append(client.get(f"{_OPENLIGA_BASE}/getmatchdata/{shortcut}/{season}"))
            league_keys.append(key)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days_ahead)

        for i, r in enumerate(results):
            if isinstance(r, Exception):
                continue
            league_key = league_keys[i]
            try:
                matches = r.json() if r.status_code == 200 else []
                for m in matches:
                    # Only upcoming matches
                    kickoff_raw = m.get("matchDateTime") or m.get("matchDateTimeUTC") or ""
                    kickoff = _parse_dt(kickoff_raw[:19]) if kickoff_raw else None
                    if not kickoff or kickoff <= now or kickoff > cutoff:
                        continue
                    if m.get("matchIsFinished"):
                        continue
                    team1 = (m.get("team1") or {}).get("teamName", "").strip()
                    team2 = (m.get("team2") or {}).get("teamName", "").strip()
                    if not team1 or not team2:
                        continue
                    mid = str(m.get("matchID") or "")
                    events.append({
                        "home_team":    team1,
                        "away_team":    team2,
                        "league":       league_key,
                        "kickoff_time": kickoff,
                        "external_id":  f"openliga-{mid}" if mid else None,
                        "status":       "upcoming",
                        "source":       "openligadb",
                    })
            except Exception as exc:
                logger.debug("[fixture-fetcher] OpenLigaDB parse error for %s: %s", league_key, exc)

    logger.info("[fixture-fetcher] OpenLigaDB: %d events", len(events))
    return events


# ── Source 4: API-Football via RapidAPI (optional) ────────────────────────────

_API_FOOTBALL_LEAGUES = {
    "premier_league":   39,
    "la_liga":          140,
    "bundesliga":       78,
    "serie_a":          135,
    "ligue_1":          61,
    "champions_league": 2,
    "eredivisie":       88,
    "primeira_liga":    94,
}


async def _fetch_api_football(days_ahead: int = 14) -> List[Dict]:
    """Fetch from API-Football (RapidAPI). Requires API_FOOTBALL_KEY env var."""
    api_key = os.getenv("API_FOOTBALL_KEY", "").strip()
    if not api_key:
        return []

    now    = datetime.now(timezone.utc)
    events: List[Dict] = []
    headers = {
        "X-RapidAPI-Key":  api_key,
        "X-RapidAPI-Host": "v3.football.api-sports.io",
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=headers) as client:
        for league_key, league_id in _API_FOOTBALL_LEAGUES.items():
            try:
                r = await client.get(
                    f"{_API_FOOTBALL_BASE}/fixtures",
                    params={
                        "league":  league_id,
                        "season":  now.year,
                        "from":    now.strftime("%Y-%m-%d"),
                        "to":      (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d"),
                        "status":  "NS",  # Not Started
                    },
                )
                if r.status_code == 200:
                    for fix in r.json().get("response", []):
                        try:
                            fix_info = fix.get("fixture", {})
                            teams    = fix.get("teams", {})
                            home     = teams.get("home", {}).get("name", "").strip()
                            away     = teams.get("away", {}).get("name", "").strip()
                            if not home or not away:
                                continue
                            kickoff = _parse_dt(fix_info.get("date"))
                            events.append({
                                "home_team":    home,
                                "away_team":    away,
                                "league":       league_key,
                                "kickoff_time": kickoff,
                                "external_id":  f"apifootball-{fix_info.get('id', '')}",
                                "status":       "upcoming",
                                "source":       "api-football",
                            })
                        except (KeyError, TypeError):
                            pass
                elif r.status_code == 429:
                    logger.warning("[fixture-fetcher] API-Football rate-limited")
                    break
            except Exception as exc:
                logger.debug("[fixture-fetcher] API-Football error for %s: %s", league_key, exc)

    logger.info("[fixture-fetcher] API-Football: %d events", len(events))
    return events


# ── Public interface ──────────────────────────────────────────────────────────

async def fetch_upcoming_multi_source(days_ahead: int = 14) -> List[Dict]:
    """
    Fetch upcoming fixtures from all available sources in parallel and merge.

    De-duplicates by (home_team, away_team, date). Sources with higher priority
    (TheSportsDB first) win on collision.

    Returns a list of normalised match dicts.
    """
    # Run all sources in parallel — each handles its own auth/rate-limit logic
    results = await asyncio.gather(
        _fetch_sportsdb_range(days_ahead),
        _fetch_football_data(days_ahead),
        _fetch_openligadb(days_ahead),
        _fetch_api_football(days_ahead),
        return_exceptions=True,
    )

    merged: Dict[str, Dict] = {}  # fingerprint → event

    for source_events in results:
        if isinstance(source_events, Exception):
            logger.warning("[fixture-fetcher] Source error: %s", source_events)
            continue
        for ev in source_events:
            home = (ev.get("home_team") or "").strip()
            away = (ev.get("away_team") or "").strip()
            ko   = ev.get("kickoff_time")
            date_str = ko.strftime("%Y-%m-%d") if isinstance(ko, datetime) else "unknown"
            fp = f"{date_str}::{home.lower()}::{away.lower()}"
            if fp not in merged:
                merged[fp] = ev

    events = list(merged.values())
    # Sort by kickoff time
    events.sort(key=lambda e: e.get("kickoff_time") or datetime.min.replace(tzinfo=timezone.utc))

    logger.info("[fixture-fetcher] Total merged: %d upcoming fixtures from all sources", len(events))
    return events


async def sync_upcoming_multi_source(db, days_ahead: int = 14) -> Dict[str, int]:
    """
    Fetch upcoming fixtures from all sources and upsert into the matches table.
    Returns {inserted, skipped, total_fetched}.
    """
    from sqlalchemy import select
    from app.db.models import Match

    events = await fetch_upcoming_multi_source(days_ahead=days_ahead)
    inserted = 0
    skipped  = 0

    for ev in events:
        home    = ev["home_team"]
        away    = ev["away_team"]
        kickoff = ev.get("kickoff_time")
        ext_id  = ev.get("external_id")
        league  = ev.get("league", "unknown")
        source  = ev.get("source", "unknown")

        if not kickoff:
            skipped += 1
            continue

        ko_naive = kickoff.replace(tzinfo=None) if kickoff.tzinfo else kickoff
        date_str = ko_naive.strftime("%Y-%m-%d")
        fp = f"{date_str}::{home.lower()}::{away.lower()}::{league}"

        try:
            existing = None
            if ext_id:
                res = await db.execute(select(Match).where(Match.external_id == ext_id))
                existing = res.scalar_one_or_none()
            if not existing:
                res = await db.execute(select(Match).where(Match.fingerprint == fp))
                existing = res.scalar_one_or_none()

            if existing:
                skipped += 1
            else:
                match = Match(
                    external_id=ext_id,
                    home_team=home,
                    away_team=away,
                    league=league,
                    kickoff_time=ko_naive,
                    status="upcoming",
                    source=source,
                    fingerprint=fp,
                )
                db.add(match)
                await db.commit()
                inserted += 1
        except Exception as exc:
            logger.debug("[fixture-fetcher] Insert error %s vs %s: %s", home, away, exc)
            await db.rollback()
            skipped += 1

    logger.info(
        "[fixture-fetcher] sync done: inserted=%d skipped=%d total=%d",
        inserted, skipped, len(events),
    )
    return {"inserted": inserted, "skipped": skipped, "total_fetched": len(events)}
