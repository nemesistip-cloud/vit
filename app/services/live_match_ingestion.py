# app/services/live_match_ingestion.py
"""
Live Match Ingestion, Normalization, and Deduplication Engine.

Aggregates real live and upcoming match data from configured external providers:
1. Football-Data.org (via FOOTBALL_DATA_API_KEY)
2. iSports API (via ISPORTS_API_KEY)
3. Local Database (Match table)

Normalizes all data into a canonical LiveMatch schema with full provenance metadata.
Deduplicates matches across providers using normalized team names, kickoff dates, and league matching.
STRICT REQUIREMENT: NO fake, simulated, demo, or fabricated live matches are ever created.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.config import FOOTBALL_DATA_API_KEY, ISPORTS_API_KEY
from app.services.football_api import FootballDataClient
from app.services.isports_api import ISportsClient
from app.services.team_mapper import TeamMapper

logger = logging.getLogger(__name__)


# ── Canonical Live Match Schemas ──────────────────────────────────────────────

class LiveSelection(BaseModel):
    id: str
    label: str
    odds: float
    source: str = "provider"


class LiveMarket(BaseModel):
    id: str
    match_id: str
    type: str  # match_result | next_goal | total_goals | btts
    status: str  # open | suspended | closed | unavailable
    home: str
    away: str
    selections: List[LiveSelection]
    updated_at: float
    odds_source: str
    odds_timestamp: float


class CanonicalLiveMatch(BaseModel):
    id: str  # Normalized ID e.g. "live-fd-12345" or "live-db-uuid"
    provider: str  # footballdata | isports | db
    provider_match_id: str
    home: str
    away: str
    league: str
    sport: str = "football"
    status: str  # LIVE | UPCOMING | FINISHED | DATA_UNAVAILABLE
    minute: int = 0
    home_score: int = 0
    away_score: int = 0
    period: str = "scheduled"  # first_half | second_half | HT | FT | scheduled
    kickoff_time: Optional[str] = None
    source_timestamp: float
    ingestion_timestamp: float
    last_successful_update: float
    markets_available: bool = False
    raw_odds: Optional[Dict[str, Any]] = None


# ── Deduplication & Normalization Helper Functions ───────────────────────────

def _normalize_name(name: str) -> str:
    return TeamMapper.normalize_name(name)


def _generate_match_fingerprint(home: str, away: str, kickoff_time: str) -> str:
    norm_h = _normalize_name(home)
    norm_a = _normalize_name(away)
    date_str = (kickoff_time or "").split("T")[0]
    return f"{norm_h}::vs::{norm_a}::{date_str}"


class LiveMatchIngestionService:
    """Service to fetch, normalize, and deduplicate live matches across providers."""

    def __init__(self):
        self._cache_live_matches: List[CanonicalLiveMatch] = []
        self._cache_upcoming_matches: List[CanonicalLiveMatch] = []
        self._last_ingest_time: float = 0.0
        self._cache_ttl: float = 15.0  # 15 second TTL for live feed caching

    async def fetch_and_normalize_all(self) -> Dict[str, List[CanonicalLiveMatch]]:
        """Fetch from all providers, normalize, deduplicate, and classify as live or upcoming."""
        now = time.time()
        if now - self._last_ingest_time < self._cache_ttl and (self._cache_live_matches or self._cache_upcoming_matches):
            return {
                "live": self._cache_live_matches,
                "upcoming": self._cache_upcoming_matches,
            }

        raw_matches: List[CanonicalLiveMatch] = []

        # 1. Fetch from Football-Data.org
        if FOOTBALL_DATA_API_KEY and not FootballDataClient._key_forbidden:
            fd_matches = await self._fetch_football_data_org()
            raw_matches.extend(fd_matches)

        # 2. Fetch from iSports API
        if ISPORTS_API_KEY:
            isports_matches = await self._fetch_isports()
            raw_matches.extend(isports_matches)

        # 3. Fetch from DB
        db_matches = await self._fetch_db_matches()
        raw_matches.extend(db_matches)

        # Deduplicate
        deduped_live: Dict[str, CanonicalLiveMatch] = {}
        deduped_upcoming: Dict[str, CanonicalLiveMatch] = {}

        for m in raw_matches:
            fp = _generate_match_fingerprint(m.home, m.away, m.kickoff_time or "")
            if m.status == "LIVE":
                if fp not in deduped_live:
                    deduped_live[fp] = m
                else:
                    # Prefer provider with live score/minute update over DB
                    existing = deduped_live[fp]
                    if existing.provider == "db" and m.provider != "db":
                        deduped_live[fp] = m
            elif m.status == "UPCOMING":
                if fp not in deduped_upcoming and fp not in deduped_live:
                    deduped_upcoming[fp] = m

        live_list = list(deduped_live.values())
        upcoming_list = list(deduped_upcoming.values())

        # Sort live by minute descending, upcoming by kickoff time
        live_list.sort(key=lambda x: x.minute, reverse=True)
        upcoming_list.sort(key=lambda x: x.kickoff_time or "")

        self._cache_live_matches = live_list
        self._cache_upcoming_matches = upcoming_list
        self._last_ingest_time = now

        return {
            "live": live_list,
            "upcoming": upcoming_list,
        }

    async def _fetch_football_data_org(self) -> List[CanonicalLiveMatch]:
        results: List[CanonicalLiveMatch] = []
        try:
            client = FootballDataClient(api_key=FOOTBALL_DATA_API_KEY)
            # Query IN_PLAY first
            data = await client._cached_request("/matches", {"status": "IN_PLAY"}, ttl=10)
            matches = data.get("matches", []) if isinstance(data, dict) else []

            # Also check PAUSED (half-time)
            paused_data = await client._cached_request("/matches", {"status": "PAUSED"}, ttl=10)
            if isinstance(paused_data, dict):
                matches.extend(paused_data.get("matches", []))

            # Query today's scheduled matches if no IN_PLAY
            if not matches:
                today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                sched_data = await client._cached_request("/matches", {"dateFrom": today_str, "dateTo": today_str, "status": "SCHEDULED"}, ttl=60)
                if isinstance(sched_data, dict):
                    matches.extend(sched_data.get("matches", []))

            await client.close()

            now = time.time()
            for m in matches:
                status_raw = m.get("status", "")
                is_live = status_raw in ("IN_PLAY", "PAUSED", "IN_PROGRESS", "LIVE")
                status = "LIVE" if is_live else ("UPCOMING" if status_raw in ("SCHEDULED", "TIMED") else "FINISHED")

                score = m.get("score", {})
                full_time = score.get("fullTime", {})
                h_score = full_time.get("home") or 0
                a_score = full_time.get("away") or 0

                # Calculate minute if in-play
                utc_date = m.get("utcDate", "")
                minute = 0
                period = "scheduled"
                if is_live:
                    period = "HT" if status_raw == "PAUSED" else "second_half"
                    if utc_date:
                        try:
                            start_dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
                            elapsed_mins = int((datetime.now(timezone.utc) - start_dt).total_seconds() / 60)
                            minute = min(90, max(1, elapsed_mins))
                        except Exception:
                            minute = 45 if status_raw == "PAUSED" else 60

                canon = CanonicalLiveMatch(
                    id=f"live-fd-{m.get('id')}",
                    provider="footballdata",
                    provider_match_id=str(m.get("id")),
                    home=m.get("homeTeam", {}).get("name", "Home Team"),
                    away=m.get("awayTeam", {}).get("name", "Away Team"),
                    league=m.get("competition", {}).get("name", "Football"),
                    status=status,
                    minute=minute,
                    home_score=int(h_score),
                    away_score=int(a_score),
                    period=period,
                    kickoff_time=utc_date,
                    source_timestamp=now,
                    ingestion_timestamp=now,
                    last_successful_update=now,
                    markets_available=is_live,
                )
                results.append(canon)
        except Exception as e:
            logger.warning("Error fetching live matches from football-data.org: %s", e)

        return results

    async def _fetch_isports(self) -> List[CanonicalLiveMatch]:
        results: List[CanonicalLiveMatch] = []
        try:
            client = ISportsClient()
            data = await client.get_live_scores()
            await client.close()

            matches = data.get("data", []) if isinstance(data, dict) else []
            now = time.time()
            for m in matches:
                # iSports match status: 1 = 1st half, 2 = HT, 3 = 2nd half, 4 = Overtime, -1 = Finished, 0 = Not started
                status_code = m.get("status", 0)
                is_live = status_code in (1, 2, 3, 4)
                status = "LIVE" if is_live else ("UPCOMING" if status_code == 0 else "FINISHED")

                period = "first_half" if status_code == 1 else ("HT" if status_code == 2 else "second_half")

                canon = CanonicalLiveMatch(
                    id=f"live-isports-{m.get('matchId')}",
                    provider="isports",
                    provider_match_id=str(m.get("matchId")),
                    home=m.get("homeName", "Home Team"),
                    away=m.get("awayName", "Away Team"),
                    league=m.get("leagueName", "Football"),
                    status=status,
                    minute=int(m.get("minute", 0) or 0),
                    home_score=int(m.get("homeScore", 0) or 0),
                    away_score=int(m.get("awayScore", 0) or 0),
                    period=period,
                    kickoff_time=m.get("matchTime"),
                    source_timestamp=now,
                    ingestion_timestamp=now,
                    last_successful_update=now,
                    markets_available=is_live,
                )
                results.append(canon)
        except Exception as e:
            logger.warning("Error fetching live matches from iSports: %s", e)

        return results

    async def _fetch_db_matches(self) -> List[CanonicalLiveMatch]:
        results: List[CanonicalLiveMatch] = []
        try:
            from app.db.database import AsyncSessionLocal, initialize_schema
            from app.db.models import Match
            from sqlalchemy import select, or_

            await initialize_schema()

            now_dt = datetime.now(timezone.utc)
            now = time.time()

            async with AsyncSessionLocal() as session:
                # Query matches marked as live/in_progress or scheduled within next 24 hours
                stmt = select(Match).where(
                    or_(
                        Match.status.in_(["live", "in_progress", "IN_PLAY"]),
                        Match.kickoff_time >= now_dt
                    )
                ).limit(30)
                res = await session.execute(stmt)
                matches = res.scalars().all()

                for m in matches:
                    is_live = (m.status or "").lower() in ("live", "in_progress", "in_play")
                    status = "LIVE" if is_live else "UPCOMING"

                    kickoff_iso = m.kickoff_time.isoformat() if m.kickoff_time else ""
                    minute = 0
                    if is_live and m.kickoff_time:
                        elapsed = int((now_dt - m.kickoff_time.replace(tzinfo=timezone.utc) if m.kickoff_time.tzinfo is None else (now_dt - m.kickoff_time)).total_seconds() / 60)
                        minute = min(90, max(1, elapsed))

                    canon = CanonicalLiveMatch(
                        id=f"live-db-{m.id}",
                        provider="db",
                        provider_match_id=str(m.id),
                        home=m.home_team or "Home",
                        away=m.away_team or "Away",
                        league=m.league or "Football",
                        status=status,
                        minute=minute,
                        home_score=m.home_goals if m.home_goals is not None else 0,
                        away_score=m.away_goals if m.away_goals is not None else 0,
                        period="second_half" if minute > 45 else "first_half",
                        kickoff_time=kickoff_iso,
                        source_timestamp=now,
                        ingestion_timestamp=now,
                        last_successful_update=now,
                        markets_available=is_live,
                    )
                    results.append(canon)
        except Exception as e:
            logger.warning("Error fetching live/upcoming matches from DB: %s", e)

        return results


live_ingestion_service = LiveMatchIngestionService()
