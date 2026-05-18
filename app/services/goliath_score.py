"""app/services/goliath_score.py — Goliath G-Score Over/Under Engine.

G = λ_attack × λ_defense × f_context × f_ref × f_momentum

Returns expected goals, over/under 1.5 / 2.5 / 3.5 probabilities
via Poisson convolution.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc

logger = logging.getLogger(__name__)

# League average goals per game (baseline λ)
LEAGUE_GOALS_PG: Dict[str, float] = {
    "premier_league": 2.72,
    "la_liga":        2.58,
    "bundesliga":     2.97,
    "serie_a":        2.51,
    "ligue_1":        2.62,
    "champions_league": 2.89,
    "europa_league":  2.74,
    "eredivisie":     3.10,
    "primera_liga":   2.58,
    "default":        2.65,
}

# League attack/defense split (home advantage λ)
LEAGUE_HOME_ATTACK_SPLIT = 0.53   # ~53% of league goals scored by home team


def _league_key(league: str) -> str:
    league = (league or "").lower().replace(" ", "_").replace("-", "_")
    for k in LEAGUE_GOALS_PG:
        if k != "default" and (k in league or league in k):
            return k
    return "default"


def _poisson_prob(lam: float, k: int) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _over_prob(home_lambda: float, away_lambda: float, threshold: float) -> float:
    """P(total goals > threshold) via Poisson convolution."""
    max_goals = 10
    prob_under_or_equal = 0.0
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            if h + a <= threshold:
                prob_under_or_equal += _poisson_prob(home_lambda, h) * _poisson_prob(away_lambda, a)
    return round(max(0.0, min(1.0, 1.0 - prob_under_or_equal)), 4)


def _btts_prob(home_lambda: float, away_lambda: float) -> float:
    """P(both teams score ≥1 goal)."""
    p_home_zero = _poisson_prob(home_lambda, 0)
    p_away_zero = _poisson_prob(away_lambda, 0)
    return round(max(0.0, (1 - p_home_zero) * (1 - p_away_zero)), 4)


async def _get_team_form_goals(db: AsyncSession, team: str, limit: int = 8) -> Dict[str, float]:
    """Return attack/defense λ for a team from recent matches."""
    try:
        from app.db.models import Match
        stmt = (
            select(Match)
            .where(
                or_(Match.home_team == team, Match.away_team == team),
                Match.home_goals.isnot(None),
                Match.away_goals.isnot(None),
            )
            .order_by(desc(Match.kickoff_time))
            .limit(limit)
        )
        rows = list((await db.execute(stmt)).scalars().all())
        if not rows:
            return {"attack": 1.35, "defense": 1.20, "n": 0}

        scored = conceded = 0
        for m in rows:
            if m.home_team == team:
                scored   += int(m.home_goals or 0)
                conceded += int(m.away_goals or 0)
            else:
                scored   += int(m.away_goals or 0)
                conceded += int(m.home_goals or 0)

        n = len(rows)
        return {
            "attack":  round(scored   / n, 4),
            "defense": round(conceded / n, 4),
            "n":       n,
        }
    except Exception as exc:
        logger.warning("[goliath] team form query failed for %s: %s", team, exc)
        return {"attack": 1.35, "defense": 1.20, "n": 0}


def _context_factor(kickoff_hour: int = 15) -> float:
    """Evening games (19-21h UTC) tend to produce slightly more goals."""
    if 19 <= kickoff_hour <= 21:
        return 1.04
    if kickoff_hour < 12:
        return 0.97  # morning kickoffs (rare, neutral)
    return 1.00


def _momentum_factor(home_form_pts: float, away_form_pts: float) -> float:
    """Teams in poor form (low pts/game) produce more chaotic / higher-scoring games."""
    avg_pts = (home_form_pts + away_form_pts) / 2
    if avg_pts < 1.0:
        return 1.06   # struggling teams — more open games
    if avg_pts > 2.2:
        return 0.96   # elite in-form teams — tighter
    return 1.00


async def compute_goliath_score(
    db: Optional[AsyncSession],
    home_team: str,
    away_team: str,
    league: str = "default",
    kickoff_hour: int = 15,
    home_form_pts: float = 1.3,
    away_form_pts: float = 1.2,
) -> Dict[str, Any]:
    """
    Compute Goliath G-Score expected goals and market probabilities.

    Returns:
        home_xg, away_xg, total_xg
        over_15, under_15
        over_25, under_25
        over_35, under_35
        btts, no_btts
        g_score (composite index 0–100)
        source
    """
    key = _league_key(league)
    league_avg = LEAGUE_GOALS_PG[key]

    # Fetch team form
    if db:
        home_form = await _get_team_form_goals(db, home_team)
        away_form = await _get_team_form_goals(db, away_team)
    else:
        home_form = {"attack": 1.40, "defense": 1.15, "n": 0}
        away_form = {"attack": 1.20, "defense": 1.35, "n": 0}

    home_attack  = home_form["attack"]  or 1.35
    home_defense = home_form["defense"] or 1.20
    away_attack  = away_form["attack"]  or 1.20
    away_defense = away_form["defense"] or 1.35

    # Blend team λ with league average (regression to mean)
    home_lambda_raw = (home_attack * (1.0 - away_defense / (away_defense + league_avg))) * LEAGUE_HOME_ATTACK_SPLIT
    away_lambda_raw = (away_attack * (1.0 - home_defense / (home_defense + league_avg))) * (1 - LEAGUE_HOME_ATTACK_SPLIT)

    # Normalize around league average split
    blend = 0.6  # 60% team data, 40% league baseline
    home_xg = round(
        blend * home_lambda_raw + (1 - blend) * league_avg * LEAGUE_HOME_ATTACK_SPLIT,
        3,
    )
    away_xg = round(
        blend * away_lambda_raw + (1 - blend) * league_avg * (1 - LEAGUE_HOME_ATTACK_SPLIT),
        3,
    )

    # Ensure reasonable range
    home_xg = max(0.20, min(home_xg, 4.0))
    away_xg = max(0.15, min(away_xg, 3.5))

    # Context & momentum adjustments
    f_ctx = _context_factor(kickoff_hour)
    f_mom = _momentum_factor(home_form_pts, away_form_pts)

    home_xg = round(home_xg * f_ctx * f_mom, 3)
    away_xg = round(away_xg * f_ctx * f_mom, 3)
    total_xg = round(home_xg + away_xg, 3)

    # Market probabilities
    over_15 = _over_prob(home_xg, away_xg, 1.5)
    over_25 = _over_prob(home_xg, away_xg, 2.5)
    over_35 = _over_prob(home_xg, away_xg, 3.5)
    btts    = _btts_prob(home_xg, away_xg)

    # G-Score composite index (0–100) — higher = more goal-intensive match expected
    g_score = round(min(100.0, (total_xg / 5.0) * 100), 1)

    feature_completeness = min(1.0, (home_form["n"] + away_form["n"]) / 16.0)

    # Tier classification
    if g_score >= 70:
        tier, verdict = "EXPLOSIVE", "High-scoring thriller expected — target Over 2.5 and BTTS"
    elif g_score >= 50:
        tier, verdict = "HIGH", "Above-average goals likely — consider Over 2.5"
    elif g_score >= 35:
        tier, verdict = "MODERATE", "Balanced match — close contest with 2–3 goals possible"
    elif g_score >= 20:
        tier, verdict = "LOW", "Tight, low-scoring encounter expected — lean Under 2.5"
    else:
        tier, verdict = "LOCKDOWN", "Both defenses dominant — strong Under 1.5 signal"

    # Win probabilities via Poisson (home/draw/away)
    max_g = 8
    home_win = draw = away_win = 0.0
    for h in range(max_g):
        ph = _poisson_prob(home_xg, h)
        for a in range(max_g):
            pa = _poisson_prob(away_xg, a)
            p = ph * pa
            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p
    total_wp = home_win + draw + away_win
    home_win_prob = round((home_win / total_wp) * 100, 1) if total_wp else 33.3
    draw_prob     = round((draw     / total_wp) * 100, 1) if total_wp else 33.3
    away_win_prob = round((away_win / total_wp) * 100, 1) if total_wp else 33.3

    return {
        "home_team":            home_team,
        "away_team":            away_team,
        "league":               league,
        "home_xg":              home_xg,
        "away_xg":              away_xg,
        "total_xg":             total_xg,
        "g_score":              g_score,
        "tier":                 tier,
        "verdict":              verdict,
        "home_win_prob":        home_win_prob,
        "draw_prob":            draw_prob,
        "away_win_prob":        away_win_prob,
        "over_15":              over_15,
        "under_15":             round(1 - over_15, 4),
        "over_25":              over_25,
        "under_25":             round(1 - over_25, 4),
        "over_35":              over_35,
        "under_35":             round(1 - over_35, 4),
        "btts":                 btts,
        "no_btts":              round(1 - btts, 4),
        "context_factor":       f_ctx,
        "momentum_factor":      f_mom,
        "feature_completeness": round(feature_completeness, 3),
        "source":               "goliath-v1",
    }
