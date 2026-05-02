"""app/agents/fixture_gap_agent.py  — Item 8: Fixture Gap Auto-Filler

Runs every 30 minutes. Detects scheduled matches that are missing
kickoff_time, league, or both teams — then attempts to fill data gaps
by querying the football-data.org free API and Gemini for fallback
enrichment.

Gap detection rules:
  - Match has status='scheduled' but kickoff_time is NULL
  - Match has home_team or away_team as empty/placeholder strings
  - Match has no league recorded

For each gap, attempts in order:
  1. Query football-data.org by team names (free tier, 10 req/min)
  2. If no API match: call Gemini to infer likely kickoff window + league
  3. Patch the DB record and log as IoT event
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from app.agents.base import BaseAgent
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)

MAX_PER_CYCLE = 8
FOOTBALL_API_BASE = "https://api.football-data.org/v4"



async def _query_football_api(home: str, away: str, fd_key: str) -> Optional[dict]:
    """Try to find the match via football-data.org free tier."""
    if not fd_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=15, headers={"X-Auth-Token": fd_key}) as client:
            resp = await client.get(
                f"{FOOTBALL_API_BASE}/matches",
                params={"status": "SCHEDULED", "limit": 50},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            for match in data.get("matches", []):
                h = match.get("homeTeam", {}).get("name", "").lower()
                a = match.get("awayTeam", {}).get("name", "").lower()
                if home.lower() in h or h in home.lower():
                    if away.lower() in a or a in away.lower():
                        return {
                            "kickoff": match.get("utcDate"),
                            "league": match.get("competition", {}).get("name", ""),
                        }
    except Exception as e:
        logger.debug("[fixture-gap] football-data API error: %s", e)
    return None


def _build_enrichment_prompt(home: str, away: str) -> str:
    return (
        f"You are a football data analyst. For this match:\n"
        f"{home} vs {away}\n\n"
        f"Return ONLY this JSON (no markdown):\n"
        f'{{\n'
        f'  "league": "likely competition name",\n'
        f'  "country": "country",\n'
        f'  "typical_kickoff_hour_utc": 15\n'
        f'}}\n'
        f"Base your answer on what league these teams most likely play in."
    )


def _is_gap_match(match) -> bool:
    """Return True if this match has a data gap worth filling."""
    missing_kickoff = match.kickoff_time is None
    bad_home = not match.home_team or match.home_team.strip() in ("", "TBD", "Unknown")
    bad_away = not match.away_team or match.away_team.strip() in ("", "TBD", "Unknown")
    missing_league = not match.league or match.league.strip() in ("", "unknown", "Unknown")
    return missing_kickoff or bad_home or bad_away or missing_league


class FixtureGapAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="fixture-gap",
            interval_seconds=30 * 60,
            initial_delay_seconds=180,
        )
        self._patched_ids: set[int] = set()

    async def run_cycle(self) -> Dict[str, Any]:
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        fd_key = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()

        from app.db.database import AsyncSessionLocal
        from app.db.models import Match
        from app.iot.processor import store_and_broadcast
        from sqlalchemy import select

        filled = skipped = 0

        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(Match)
                .where(Match.status.in_(["scheduled", "upcoming"]))
                .order_by(Match.id.asc())
                .limit(50)
            )
            matches = res.scalars().all()

            gap_matches = [
                m for m in matches
                if _is_gap_match(m) and m.id not in self._patched_ids
            ][:MAX_PER_CYCLE]

            for match in gap_matches:
                patched = False

                # Try football-data.org API first
                if match.home_team and match.away_team:
                    api_data = await _query_football_api(
                        match.home_team, match.away_team, fd_key
                    )
                    if api_data:
                        if not match.kickoff_time and api_data.get("kickoff"):
                            try:
                                match.kickoff_time = datetime.fromisoformat(
                                    api_data["kickoff"].replace("Z", "+00:00")
                                )
                                patched = True
                            except Exception:
                                pass
                        if not match.league and api_data.get("league"):
                            match.league = api_data["league"]
                            patched = True

                # Fallback: Gemini enrichment for league
                if not match.league and match.home_team and match.away_team and gemini_key:
                    prompt = _build_enrichment_prompt(match.home_team, match.away_team)
                    raw = await _call_gemini(prompt, gemini_key)
                    if raw:
                        try:
                            obj_match = re.search(r"\{[\s\S]*\}", raw.strip())
                            if obj_match:
                                import json
                                info = json.loads(obj_match.group())
                                league = info.get("league", "")
                                if league and league.lower() not in ("unknown", ""):
                                    match.league = league
                                    patched = True
                        except Exception:
                            pass

                if patched:
                    filled += 1
                    self._patched_ids.add(match.id)
                    logger.info(
                        "[fixture-gap] patched match=%d %s vs %s",
                        match.id, match.home_team, match.away_team,
                    )
                    await store_and_broadcast(
                        source="agent",
                        event_type="fixture_gap_filled",
                        match_id=match.id,
                        payload={
                            "match": f"{match.home_team} vs {match.away_team}",
                            "league": match.league,
                        },
                    )
                else:
                    skipped += 1
                    self._patched_ids.add(match.id)

                await asyncio.sleep(1.0)

            if filled > 0:
                await db.commit()

        result = {"gap_matches_found": len(gap_matches), "filled": filled, "skipped": skipped}
        logger.info("[fixture-gap] cycle: %s", result)
        return result
