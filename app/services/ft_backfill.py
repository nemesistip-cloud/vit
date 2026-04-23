"""
FT (full-time) results backfill service.

Two-pronged strategy for past matches that still show as
scheduled/upcoming/live without scores:

1. Real-source matches (source in {footballdata, odds_api, ...} OR
   external_id looks like a real provider ID): hand off to
   `results_settler.settle_results()` which queries Football-Data.org.

2. Local-only matches (source in {seed, synthetic, manual_upload, unknown}
   with no real provider counterpart): simulate a plausible FT score
   *deterministically* from opening odds + fingerprint, so re-runs always
   produce the same result. Stamped with `source='<original>+sim_ft'`
   and `actual_outcome` set, status -> 'completed'.

The simulator never overwrites a match that already has scores or that
the real-API settler has already filled in.
"""

from __future__ import annotations

import hashlib
import logging
import random
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.db.models import Match

logger = logging.getLogger(__name__)


REAL_SOURCES = {"footballdata", "football_data", "odds_api", "sportmonks", "api_football"}
SIM_LEAGUE_GOAL_AVG = {
    "premier_league": 2.85, "la_liga": 2.55, "bundesliga": 3.15,
    "serie_a": 2.65, "ligue_1": 2.70, "championship": 2.55,
    "eredivisie": 3.05, "primeira_liga": 2.50, "scottish_premiership": 2.95,
    "belgian_pro_league": 2.90, "ucl": 2.95, "uel": 2.85,
}
DEFAULT_AVG_GOALS = 2.70


def _outcome(home_g: int, away_g: int) -> str:
    if home_g > away_g: return "home"
    if home_g < away_g: return "away"
    return "draw"


def _seed_for(match: Match) -> int:
    """Deterministic RNG seed from fingerprint or id+kickoff."""
    raw = match.fingerprint or f"{match.id}:{match.home_team}:{match.away_team}:{match.kickoff_time}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12], 16)


def _normalise_league(league: Optional[str]) -> str:
    if not league:
        return ""
    return league.strip().lower().replace(" ", "_")


def _avg_goals_for_league(league: Optional[str]) -> float:
    return SIM_LEAGUE_GOAL_AVG.get(_normalise_league(league), DEFAULT_AVG_GOALS)


def _implied_probs_from_odds(home_o: Optional[float], draw_o: Optional[float], away_o: Optional[float]):
    """Convert opening odds to a normalised P(home/draw/away). Returns None if odds incomplete."""
    if not (home_o and draw_o and away_o) or min(home_o, draw_o, away_o) <= 1.01:
        return None
    raw = (1.0 / home_o, 1.0 / draw_o, 1.0 / away_o)
    s = sum(raw)
    if s <= 0:
        return None
    return raw[0] / s, raw[1] / s, raw[2] / s


def _simulate_ft_score(match: Match) -> tuple[int, int]:
    """
    Deterministic simulator: pick total goals from a Poisson-ish lookup centred on the
    league average, then split by 1X2 implied probability (or 45/27/28 fallback).
    """
    rng = random.Random(_seed_for(match))
    total_avg = _avg_goals_for_league(match.league)

    # Total goals: pick from a small distribution around league average
    bands = [
        (0, 0.10),
        (1, 0.20),
        (2, 0.27),
        (3, 0.22),
        (4, 0.13),
        (5, 0.05),
        (6, 0.03),
    ]
    # Skew the distribution toward total_avg (re-weight)
    total_goals = rng.choices(
        [b[0] for b in bands],
        weights=[max(0.001, b[1] * (1.0 + 0.15 * (b[0] - 2)) * (total_avg / 2.7)) for b in bands],
        k=1,
    )[0]

    probs = _implied_probs_from_odds(
        match.opening_odds_home, match.opening_odds_draw, match.opening_odds_away
    ) or (0.45, 0.27, 0.28)

    outcome = rng.choices(["home", "draw", "away"], weights=probs, k=1)[0]

    if outcome == "draw":
        h = a = total_goals // 2
        if total_goals % 2 == 1:
            # Odd total can't be a draw — bump or split
            if total_goals == 1:
                return 0, 0
            h = a = (total_goals - 1) // 2 + 1
            return h - 1, a - 1 if h - 1 >= 0 else 0
        return h, a
    if outcome == "home":
        # Home wins by at least 1
        margin = max(1, rng.choices([1, 2, 3], weights=[0.55, 0.30, 0.15], k=1)[0])
        margin = min(margin, total_goals if total_goals > 0 else 1)
        away = max(0, (total_goals - margin) // 2)
        home = total_goals - away if total_goals - away > away else away + margin
        return home, away
    # away
    margin = max(1, rng.choices([1, 2, 3], weights=[0.55, 0.30, 0.15], k=1)[0])
    margin = min(margin, total_goals if total_goals > 0 else 1)
    home = max(0, (total_goals - margin) // 2)
    away = total_goals - home if total_goals - home > home else home + margin
    return home, away


def _is_real_source(match: Match) -> bool:
    src = (match.source or "").lower()
    if src in REAL_SOURCES:
        return True
    ext = (match.external_id or "").strip()
    # Heuristic: numeric external IDs are typically real provider IDs;
    # vit_seed_* / syn_* are local-only.
    if ext and ext.isdigit():
        return True
    return False


async def backfill_ft_results(
    db: Optional[AsyncSession] = None,
    *,
    settle_real_first: bool = True,
    simulate_local: bool = True,
    days_back: int = 30,
) -> dict:
    """
    Run the full backfill:
      1. Optional: settle_results() against Football-Data.org (real matches).
      2. Simulate FT results for any remaining past local-only matches.

    Returns a structured summary with counts per category.
    """
    summary: dict = {
        "settled_real": 0,
        "simulated_local": 0,
        "skipped_already_finished": 0,
        "skipped_future": 0,
        "skipped_real_no_api": 0,
        "errors": 0,
        "details": [],
    }

    # Phase 1 — real-API settlement
    if settle_real_first:
        try:
            from app.services.results_settler import settle_results
            real_summary = await settle_results(days_back=min(days_back, 7))
            summary["settled_real"] = int(real_summary.get("settled") or 0)
            summary["real_settler_message"] = real_summary.get("message")
        except Exception as e:
            logger.warning(f"Real settle pass failed: {e}", exc_info=True)
            summary["errors"] += 1

    # Phase 2 — simulate local-only matches
    if not simulate_local:
        return summary

    own_session = db is None
    session: AsyncSession = db or AsyncSessionLocal()

    try:
        if own_session:
            session = AsyncSessionLocal()
            await session.__aenter__()  # type: ignore[attr-defined]

        now_utc = datetime.now(timezone.utc)
        # Pull all matches whose kickoff is in the past and not yet completed
        rows = (await session.execute(
            select(Match).where(
                Match.kickoff_time < now_utc,
                Match.status.notin_(["completed", "finished", "ft", "FT"]),
            )
        )).scalars().all()

        for m in rows:
            try:
                if m.home_goals is not None and m.away_goals is not None:
                    summary["skipped_already_finished"] += 1
                    continue
                if _is_real_source(m):
                    # Real-source past match without scores — settle pass should have
                    # picked it up. If it didn't, the API key is probably missing or
                    # the match isn't in Football-Data.org's coverage. Skip rather
                    # than fabricate.
                    summary["skipped_real_no_api"] += 1
                    continue
                hg, ag = _simulate_ft_score(m)
                m.home_goals = hg
                m.away_goals = ag
                m.actual_outcome = _outcome(hg, ag)
                m.status = "completed"
                # Tag the source so audits can tell simulated FT apart from real
                base_src = (m.source or "unknown").split("+")[0]
                if "+sim_ft" not in (m.source or ""):
                    m.source = f"{base_src}+sim_ft"
                summary["simulated_local"] += 1
                summary["details"].append({
                    "id": m.id,
                    "home": m.home_team, "away": m.away_team,
                    "league": m.league,
                    "score": f"{hg}-{ag}",
                    "outcome": m.actual_outcome,
                    "source": m.source,
                })
            except Exception as e:
                logger.warning(f"Simulate FT failed for match {m.id}: {e}")
                summary["errors"] += 1

        await session.commit()
    finally:
        if own_session:
            try:
                await session.__aexit__(None, None, None)  # type: ignore[attr-defined]
            except Exception:
                pass

    return summary
