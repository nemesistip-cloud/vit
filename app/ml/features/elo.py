"""app/ml/features/elo.py — Team ELO Rating System.

Maintains ELO ratings for all teams in the database.
Ratings update after each settled match using standard ELO formula.
ELO difference is used as a feature in the prediction engine.

Usage:
    elo_system = TeamEloSystem()
    await elo_system.update_from_match(db, match)
    diff = await elo_system.get_elo_diff(db, home_team, away_team)
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

logger = logging.getLogger(__name__)

_DEFAULT_ELO    = 1500
_K_FACTOR       = 32           # Standard K-factor
_K_FACTOR_NEW   = 40           # Higher K for teams with < 20 matches
_HOME_ADVANTAGE = 50           # Home side gets +50 ELO points for expected score
_MAX_ELO        = 2200
_MIN_ELO        = 800


def _expected_score(rating_a: float, rating_b: float) -> float:
    """ELO expected score for team A against team B."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def _elo_update(
    rating_a: float, rating_b: float,
    score_a: float,           # 1.0 = win, 0.5 = draw, 0.0 = loss
    k_a: float = _K_FACTOR,
    k_b: float = _K_FACTOR,
) -> Tuple[float, float]:
    """Return (new_rating_a, new_rating_b) after a match."""
    expected_a = _expected_score(rating_a, rating_b)
    expected_b = 1.0 - expected_a
    score_b    = 1.0 - score_a

    new_a = rating_a + k_a * (score_a - expected_a)
    new_b = rating_b + k_b * (score_b - expected_b)

    return (
        max(_MIN_ELO, min(_MAX_ELO, round(new_a, 1))),
        max(_MIN_ELO, min(_MAX_ELO, round(new_b, 1))),
    )


async def _ensure_table(db: AsyncSession) -> bool:
    """Create team_elo table if it doesn't exist (SQLite-safe)."""
    try:
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS team_elo (
                id SERIAL PRIMARY KEY,
                team_name VARCHAR(100) NOT NULL,
                league VARCHAR(50) NOT NULL DEFAULT 'default',
                elo_rating FLOAT NOT NULL DEFAULT 1500,
                matches_played INTEGER NOT NULL DEFAULT 0,
                last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(team_name, league)
            )
        """))
        await db.commit()
        return True
    except Exception:
        try:
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS team_elo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_name VARCHAR(100) NOT NULL,
                    league VARCHAR(50) NOT NULL DEFAULT 'default',
                    elo_rating REAL NOT NULL DEFAULT 1500,
                    matches_played INTEGER NOT NULL DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(team_name, league)
                )
            """))
            await db.commit()
            return True
        except Exception as exc2:
            logger.warning("[elo] table creation failed: %s", exc2)
            return False


async def get_elo_rating(
    db: AsyncSession, team_name: str, league: str = "default"
) -> Tuple[float, int]:
    """Return (elo_rating, matches_played) for a team. Returns defaults if not found."""
    try:
        result = await db.execute(text(
            "SELECT elo_rating, matches_played FROM team_elo "
            "WHERE team_name = :t AND league = :l"
        ), {"t": team_name, "l": league or "default"})
        row = result.fetchone()
        if row:
            return float(row[0]), int(row[1])
    except Exception as exc:
        logger.debug("[elo] get_elo_rating error for %s: %s", team_name, exc)
    return _DEFAULT_ELO, 0


async def upsert_elo_rating(
    db: AsyncSession,
    team_name: str,
    league: str,
    new_elo: float,
    matches_played: int,
) -> None:
    """Upsert team ELO rating in the team_elo table."""
    try:
        now = datetime.now(timezone.utc)
        # Try PostgreSQL upsert first
        try:
            await db.execute(text("""
                INSERT INTO team_elo (team_name, league, elo_rating, matches_played, last_updated)
                VALUES (:t, :l, :elo, :mp, :ts)
                ON CONFLICT (team_name, league) DO UPDATE
                    SET elo_rating = :elo, matches_played = :mp, last_updated = :ts
            """), {"t": team_name, "l": league, "elo": new_elo, "mp": matches_played, "ts": now})
        except Exception:
            # SQLite fallback
            await db.execute(text("""
                INSERT OR REPLACE INTO team_elo (team_name, league, elo_rating, matches_played, last_updated)
                VALUES (:t, :l, :elo, :mp, :ts)
            """), {"t": team_name, "l": league, "elo": new_elo, "mp": matches_played, "ts": str(now)})
        await db.commit()
    except Exception as exc:
        logger.warning("[elo] upsert failed for %s: %s", team_name, exc)
        try:
            await db.rollback()
        except Exception:
            pass


async def update_elo_from_match(
    db: AsyncSession,
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
    league: str = "default",
) -> Dict[str, float]:
    """
    Update ELO ratings for both teams after a settled match.

    Returns dict with home_before, home_after, away_before, away_after,
    home_change, away_change.
    """
    await _ensure_table(db)

    home_elo, home_mp = await get_elo_rating(db, home_team, league)
    away_elo, away_mp = await get_elo_rating(db, away_team, league)

    # Home advantage adjustment for expected score calculation
    home_elo_adj = home_elo + _HOME_ADVANTAGE

    # Determine actual score
    if home_goals > away_goals:
        score_home = 1.0
    elif home_goals == away_goals:
        score_home = 0.5
    else:
        score_home = 0.0

    # K-factor based on experience
    k_home = _K_FACTOR_NEW if home_mp < 20 else _K_FACTOR
    k_away = _K_FACTOR_NEW if away_mp < 20 else _K_FACTOR

    new_home, new_away = _elo_update(
        home_elo_adj, away_elo, score_home, k_home, k_away
    )
    # Remove home advantage offset from stored rating
    new_home = max(_MIN_ELO, min(_MAX_ELO, new_home - _HOME_ADVANTAGE))

    await upsert_elo_rating(db, home_team, league, new_home, home_mp + 1)
    await upsert_elo_rating(db, away_team, league, new_away, away_mp + 1)

    return {
        "home_before":  home_elo,
        "home_after":   new_home,
        "home_change":  round(new_home - home_elo, 1),
        "away_before":  away_elo,
        "away_after":   new_away,
        "away_change":  round(new_away - away_elo, 1),
    }


async def get_elo_diff(
    db: AsyncSession,
    home_team: str,
    away_team: str,
    league: str = "default",
) -> float:
    """
    Return ELO difference (home - away) for use as a prediction feature.
    Positive = home advantage. Range typically -400 to +400.
    """
    try:
        home_elo, _ = await get_elo_rating(db, home_team, league)
        away_elo, _ = await get_elo_rating(db, away_team, league)
        return round(home_elo - away_elo, 1)
    except Exception as exc:
        logger.debug("[elo] get_elo_diff error: %s", exc)
        return 0.0


class TeamEloSystem:
    """High-level interface for team ELO operations."""

    async def get_elo_diff(
        self,
        db: AsyncSession,
        home_team: str,
        away_team: str,
        league: str = "default",
    ) -> float:
        return await get_elo_diff(db, home_team, away_team, league)

    async def update_from_match(
        self,
        db: AsyncSession,
        match,  # Match ORM object
    ) -> Dict[str, float]:
        if match.home_goals is None or match.away_goals is None:
            return {}
        return await update_elo_from_match(
            db=db,
            home_team=match.home_team,
            away_team=match.away_team,
            home_goals=int(match.home_goals),
            away_goals=int(match.away_goals),
            league=match.league or "default",
        )

    async def bulk_load_from_db(self, db: AsyncSession) -> int:
        """Re-compute ELO from all settled matches in DB (bootstrap)."""
        await _ensure_table(db)
        from app.db.models import Match
        from sqlalchemy import select

        stmt = (
            select(Match)
            .where(
                Match.home_goals.isnot(None),
                Match.away_goals.isnot(None),
            )
            .order_by(Match.kickoff_time)
        )
        matches = list((await db.execute(stmt)).scalars().all())
        for m in matches:
            await update_elo_from_match(
                db=db,
                home_team=m.home_team,
                away_team=m.away_team,
                home_goals=int(m.home_goals),
                away_goals=int(m.away_goals),
                league=m.league or "default",
            )
        logger.info("[elo] bulk_load_from_db: processed %d matches", len(matches))
        return len(matches)


# Singleton
_elo_system: Optional[TeamEloSystem] = None


def get_elo_system() -> TeamEloSystem:
    global _elo_system
    if _elo_system is None:
        _elo_system = TeamEloSystem()
    return _elo_system
