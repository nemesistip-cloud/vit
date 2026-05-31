"""app/agents/fixture_gap_agent.py — Fixture Gap Auto-Filler + Real Fixture Importer

Runs every 30 minutes. Two responsibilities:

1. IMPORT: Pulls real upcoming + past fixtures from TheSportsDB (free, no auth)
   and inserts any new ones into the DB, replacing the need for synthetic data.

2. GAP-FILL: Detects existing matches with missing kickoff_time, league, or team
   names — then uses the AI cascade to infer and patch the gaps.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict

from app.agents.base import BaseAgent
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)

MAX_GAP_PER_CYCLE = 8


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
            initial_delay_seconds=60,
        )
        self._patched_ids: set[int] = set()

    # ── Real-fixture import ────────────────────────────────────────────────────

    async def _import_real_fixtures(self) -> int:
        """Fetch real fixtures from TheSportsDB and upsert into the DB.

        Returns the number of new matches inserted.
        """
        try:
            from app.services.sportsdb_api import fetch_all_real_fixtures
            from app.db.database import AsyncSessionLocal
            from app.db.models import Match
            from app.data.match_dedup import compute_fingerprint, find_existing_match
            from sqlalchemy import select, delete

            fixtures = await fetch_all_real_fixtures()
            all_events = fixtures.get("past", []) + fixtures.get("upcoming", [])

            if not all_events:
                logger.info("[fixture-gap] TheSportsDB returned 0 events this cycle")
                return 0

            inserted = 0
            async with AsyncSessionLocal() as db:
                # Purge stale synthetic data on first import run
                synth_count_res = await db.execute(
                    select(Match).where(Match.source == "synthetic")
                )
                synth_matches = synth_count_res.scalars().all()
                if synth_matches:
                    synth_ids = [m.id for m in synth_matches]
                    # Delete predictions for synthetic matches
                    try:
                        from app.db.models import Prediction
                        await db.execute(
                            delete(Prediction).where(Prediction.match_id.in_(synth_ids))
                        )
                    except Exception:
                        pass
                    # Delete agent insights (they're all based on synthetic data initially)
                    try:
                        from app.db.models import AgentInsight
                        await db.execute(delete(AgentInsight))
                    except Exception:
                        pass
                    await db.execute(
                        delete(Match).where(Match.source == "synthetic")
                    )
                    await db.commit()
                    logger.info("[fixture-gap] purged %d synthetic matches", len(synth_ids))

                for ev in all_events:
                    ext_id = ev.get("external_id", "")
                    home   = ev["home_team"]
                    away   = ev["away_team"]
                    league = ev["league"]
                    ko     = ev.get("kickoff_time")
                    status = ev.get("status", "upcoming")

                    # Skip duplicates by external_id
                    if ext_id:
                        from sqlalchemy import select as _sel
                        existing = (await db.execute(
                            _sel(Match).where(Match.external_id == ext_id)
                        )).scalar_one_or_none()
                        if existing:
                            # Update score/status on settled matches
                            if status == "settled" and existing.status != "settled":
                                existing.status        = "settled"
                                existing.home_goals    = ev.get("home_goals")
                                existing.away_goals    = ev.get("away_goals")
                                existing.actual_outcome = ev.get("actual_outcome")
                                existing.updated_at    = datetime.now(timezone.utc)
                            continue

                    # Dedup by fingerprint
                    ko_naive = ko.replace(tzinfo=None) if ko and ko.tzinfo else ko
                    fp = compute_fingerprint(home, away, ko_naive, league)
                    fp_existing = await find_existing_match(db, home, away, ko_naive, league)
                    if fp_existing:
                        continue

                    new_match = Match(
                        external_id  = ext_id or None,
                        home_team    = home,
                        away_team    = away,
                        league       = league,
                        kickoff_time = ko_naive,
                        status       = status,
                        source       = "sportsdb",
                        fingerprint  = fp,
                        home_goals   = ev.get("home_goals"),
                        away_goals   = ev.get("away_goals"),
                        actual_outcome = ev.get("actual_outcome"),
                    )
                    db.add(new_match)
                    inserted += 1

                if inserted > 0:
                    await db.commit()
                    logger.info("[fixture-gap] imported %d real fixtures from TheSportsDB", inserted)

            return inserted
        except Exception as exc:
            logger.warning("[fixture-gap] real fixture import failed: %s", exc)
            return 0

    # ── Gap-fill cycle ─────────────────────────────────────────────────────────

    async def run_cycle(self) -> Dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.db.models import Match
        from app.iot.processor import store_and_broadcast
        from sqlalchemy import select

        # Step 1: import real fixtures
        imported = await self._import_real_fixtures()

        # Step 2: fill gaps in existing matches
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
            ][:MAX_GAP_PER_CYCLE]

            for match in gap_matches:
                patched = False

                if not match.league and match.home_team and match.away_team:
                    prompt = _build_enrichment_prompt(match.home_team, match.away_team)
                    raw = await call_ai(prompt, max_tokens=200)
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
                        "[fixture-gap] patched match=%d %s vs %s → league=%s",
                        match.id, match.home_team, match.away_team, match.league,
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

        result = {
            "real_fixtures_imported": imported,
            "gap_matches_found": len(gap_matches),
            "filled": filled,
            "skipped": skipped,
        }
        logger.info("[fixture-gap] cycle: %s", result)
        return result
