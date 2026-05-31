"""
Match deduplication utilities.

Provides:
- compute_fingerprint(): stable cross-source identifier for a fixture
- normalize_team_name(): lowercase, strip suffixes/diacritics
- find_existing_match(): returns the canonical Match if a fixture with
  the same fingerprint already exists in the DB.

This prevents API providers from re-creating fixtures that were
already manually uploaded, seeded, or pulled from another provider.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Match


_TEAM_SUFFIXES = (
    " fc", " afc", " cf", " sc", " sk", " bk", " ac",
    " club", " calcio", " olympique", " futbol club",
)

_LEAGUE_ALIASES = {
    "epl": "premier_league",
    "english_premier_league": "premier_league",
    "premier league": "premier_league",
    "premier-league": "premier_league",
    "la liga": "la_liga",
    "primera division": "la_liga",
    "primera_division": "la_liga",
    "serie a": "serie_a",
    "ligue 1": "ligue_1",
    "ligue1": "ligue_1",
    "championship": "championship",
}


def normalize_team_name(name: str) -> str:
    if not name:
        return ""
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    n = n.lower().strip()
    for suf in _TEAM_SUFFIXES:
        if n.endswith(suf):
            n = n[: -len(suf)]
    n = re.sub(r"[^a-z0-9]+", "_", n).strip("_")
    return n


def normalize_league(league: Optional[str]) -> str:
    if not league:
        return "unknown"
    raw = league.strip().lower()
    return _LEAGUE_ALIASES.get(raw, re.sub(r"[^a-z0-9]+", "_", raw).strip("_"))


def compute_fingerprint(
    home_team: str,
    away_team: str,
    kickoff: datetime | date | str,
    league: Optional[str] = None,
) -> str:
    """
    Returns a stable identifier of the form:
        YYYY-MM-DD::home_norm::away_norm::league_norm
    """
    if isinstance(kickoff, str):
        try:
            kickoff = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
        except Exception:
            return ""
    if isinstance(kickoff, datetime):
        date_str = kickoff.strftime("%Y-%m-%d")
    else:
        date_str = kickoff.strftime("%Y-%m-%d")
    return "::".join([
        date_str,
        normalize_team_name(home_team),
        normalize_team_name(away_team),
        normalize_league(league),
    ])


async def find_existing_match(
    db: AsyncSession,
    home_team: str,
    away_team: str,
    kickoff: datetime,
    league: Optional[str] = None,
) -> Optional[Match]:
    """
    Look up an existing match by computed fingerprint.
    Returns the Match row or None.
    """
    fp = compute_fingerprint(home_team, away_team, kickoff, league)
    if not fp:
        return None
    res = await db.execute(select(Match).where(Match.fingerprint == fp))
    return res.scalar_one_or_none()


async def backfill_fingerprints(db: AsyncSession, batch_size: int = 500) -> int:
    """
    One-time helper to populate fingerprint for legacy rows.
    Returns the number of rows updated.
    """
    updated = 0
    while True:
        res = await db.execute(
            select(Match).where(Match.fingerprint.is_(None)).limit(batch_size)
        )
        rows = res.scalars().all()
        if not rows:
            break
        for m in rows:
            m.fingerprint = compute_fingerprint(
                m.home_team, m.away_team, m.kickoff_time, m.league
            )
            if not m.source:
                m.source = "unknown"
            updated += 1
        await db.commit()
        if len(rows) < batch_size:
            break
    return updated
