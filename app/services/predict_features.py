"""
Predict-time feature builder.

Given the participants in an upcoming match, query the DB for recent results
and produce the per-team rolling features the sklearn model heads expect.

Replaces the hardcoded global averages that previously lived inline in
`services/ml_service/models/model_orchestrator._sklearn_predict`.

Returns a dict that mirrors the feature_map in `_sklearn_predict` so it can
be merged in directly:

    home_form_pts_5/10, away_form_pts_5/10,
    home_gf_pg_5/10,    away_gf_pg_5/10,
    home_ga_pg_5/10,    away_ga_pg_5/10,
    h2h_home_win_pct, h2h_draw_pct, h2h_away_win_pct,
    h2h_home_goals_pg, h2h_away_goals_pg,
    home_adv_league,
    elo_diff,
    feature_completeness  ← 0..1, 1 = full real data, 0 = pure fallback

Designed to be cheap (≤4 small queries) so it can run on every /predict call.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Match

logger = logging.getLogger(__name__)

# League-level home advantage estimates (goals). Empty = neutral default.
_LEAGUE_HOME_ADV: Dict[str, float] = {
    "premier_league": 0.42,
    "la_liga":        0.45,
    "bundesliga":     0.38,
    "serie_a":        0.40,
    "ligue_1":        0.35,
}
_DEFAULT_HOME_ADV = 0.40

# Neutral fallbacks used only when there's no historical data at all.
_FALLBACK_FEATURES: Dict[str, float] = {
    "home_form_pts_5":   1.30, "away_form_pts_5":   1.20,
    "home_form_pts_10":  1.30, "away_form_pts_10":  1.20,
    "home_gf_pg_5":      1.45, "away_gf_pg_5":      1.20,
    "home_ga_pg_5":      1.20, "away_ga_pg_5":      1.45,
    "home_gf_pg_10":     1.45, "away_gf_pg_10":     1.20,
    "home_ga_pg_10":     1.20, "away_ga_pg_10":     1.45,
    "h2h_home_win_pct":  0.45, "h2h_draw_pct":      0.27,
    "h2h_away_win_pct":  0.28,
    "h2h_home_goals_pg": 1.45, "h2h_away_goals_pg": 1.20,
    "home_adv_league":   _DEFAULT_HOME_ADV,
    "elo_diff":          0.0,
    "feature_completeness": 0.0,
}


async def _recent_matches_for(
    db: AsyncSession, team: str, limit: int = 10
) -> List[Match]:
    """Most-recent settled matches for a team (home or away), newest first."""
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
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def _h2h_matches(
    db: AsyncSession, home: str, away: str, limit: int = 10
) -> List[Match]:
    stmt = (
        select(Match)
        .where(
            and_(
                or_(
                    and_(Match.home_team == home, Match.away_team == away),
                    and_(Match.home_team == away, Match.away_team == home),
                ),
                Match.home_goals.isnot(None),
                Match.away_goals.isnot(None),
            )
        )
        .order_by(desc(Match.kickoff_time))
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


def _form_block(team: str, matches: List[Match], window: int) -> Dict[str, float]:
    """Compute (points/game, goals_for/game, goals_against/game) over window."""
    sliced = matches[:window]
    if not sliced:
        return {"pts_pg": 1.25, "gf_pg": 1.30, "ga_pg": 1.30, "n": 0}

    pts = gf = ga = 0
    for m in sliced:
        if m.home_team == team:
            tg, og = int(m.home_goals or 0), int(m.away_goals or 0)
        else:
            tg, og = int(m.away_goals or 0), int(m.home_goals or 0)
        gf += tg
        ga += og
        if tg > og:
            pts += 3
        elif tg == og:
            pts += 1
    n = len(sliced)
    return {
        "pts_pg": round(pts / n, 4),
        "gf_pg":  round(gf / n, 4),
        "ga_pg":  round(ga / n, 4),
        "n":      n,
    }


def _h2h_block(home: str, away: str, matches: List[Match]) -> Dict[str, float]:
    """Win-rate split + goals-per-game from the home team's perspective."""
    if not matches:
        return {
            "home_wr": 0.45, "draw_wr": 0.27, "away_wr": 0.28,
            "home_gpg": 1.45, "away_gpg": 1.20, "n": 0,
        }
    h_wins = draws = a_wins = 0
    h_goals = a_goals = 0
    for m in matches:
        # Normalise to "home-team" perspective regardless of which side they were on
        if m.home_team == home:
            hg, ag = int(m.home_goals or 0), int(m.away_goals or 0)
        else:
            hg, ag = int(m.away_goals or 0), int(m.home_goals or 0)
        h_goals += hg
        a_goals += ag
        if hg > ag:
            h_wins += 1
        elif hg == ag:
            draws += 1
        else:
            a_wins += 1
    n = len(matches)
    return {
        "home_wr":  round(h_wins / n, 4),
        "draw_wr":  round(draws / n, 4),
        "away_wr":  round(a_wins / n, 4),
        "home_gpg": round(h_goals / n, 4),
        "away_gpg": round(a_goals / n, 4),
        "n":        n,
    }


def _elo_proxy(home_form: Dict[str, float], away_form: Dict[str, float]) -> float:
    """
    Cheap ELO-delta proxy from form differential.

    +400 ≈ heavy home favourite, -400 ≈ heavy away favourite, 0 = balanced.
    Real ELO is computed elsewhere; this is a strong-enough signal for the
    sklearn heads when ELO state isn't available.
    """
    h_strength = home_form["pts_pg"] + 0.6 * home_form["gf_pg"] - 0.5 * home_form["ga_pg"]
    a_strength = away_form["pts_pg"] + 0.6 * away_form["gf_pg"] - 0.5 * away_form["ga_pg"]
    return round((h_strength - a_strength) * 90.0, 2)


async def build_predict_features(
    db: Optional[AsyncSession],
    home_team: str,
    away_team: str,
    league: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns a feature dict ready to merge into the orchestrator `features` arg.

    Resilient by design: every block has its own try/except. If the DB is
    unavailable or there is no history at all, the function returns the
    fallback feature set with `feature_completeness=0.0` so downstream
    diagnostics can detect this.
    """
    if db is None:
        logger.warning(
            "FEATURE_FALLBACK db=None for %s vs %s — returning full neutral "
            "fallback feature set (predictions will not be data-grounded)",
            home_team, away_team,
        )
        return dict(_FALLBACK_FEATURES)

    out: Dict[str, Any] = {}
    completeness_signals: List[float] = []

    try:
        home_recent = await _recent_matches_for(db, home_team, limit=10)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"home recent fetch failed for {home_team}: {exc}")
        home_recent = []
    try:
        away_recent = await _recent_matches_for(db, away_team, limit=10)
    except Exception as exc:  # pragma: no cover
        logger.warning(f"away recent fetch failed for {away_team}: {exc}")
        away_recent = []
    try:
        h2h = await _h2h_matches(db, home_team, away_team, limit=10)
    except Exception as exc:  # pragma: no cover
        logger.warning(f"h2h fetch failed for {home_team} vs {away_team}: {exc}")
        h2h = []

    # Explicit fallback warnings — operators must see when the feature
    # builder is running on cold-start defaults instead of real history.
    if not home_recent:
        logger.warning(
            "FEATURE_FALLBACK home=%s — no historical matches in DB, "
            "using neutral form/GF/GA defaults",
            home_team,
        )
    if not away_recent:
        logger.warning(
            "FEATURE_FALLBACK away=%s — no historical matches in DB, "
            "using neutral form/GF/GA defaults",
            away_team,
        )
    if not h2h:
        logger.info(
            "FEATURE_FALLBACK h2h=%s vs %s — no head-to-head history, "
            "using neutral H2H split",
            home_team, away_team,
        )

    home_5  = _form_block(home_team, home_recent, window=5)
    home_10 = _form_block(home_team, home_recent, window=10)
    away_5  = _form_block(away_team, away_recent, window=5)
    away_10 = _form_block(away_team, away_recent, window=10)
    h2h_b   = _h2h_block(home_team, away_team, h2h)

    out.update({
        "home_form_pts_5":   home_5["pts_pg"],
        "away_form_pts_5":   away_5["pts_pg"],
        "home_form_pts_10":  home_10["pts_pg"],
        "away_form_pts_10":  away_10["pts_pg"],
        "home_gf_pg_5":      home_5["gf_pg"],
        "away_gf_pg_5":      away_5["gf_pg"],
        "home_ga_pg_5":      home_5["ga_pg"],
        "away_ga_pg_5":      away_5["ga_pg"],
        "home_gf_pg_10":     home_10["gf_pg"],
        "away_gf_pg_10":     away_10["gf_pg"],
        "home_ga_pg_10":     home_10["ga_pg"],
        "away_ga_pg_10":     away_10["ga_pg"],
        "h2h_home_win_pct":  h2h_b["home_wr"],
        "h2h_draw_pct":      h2h_b["draw_wr"],
        "h2h_away_win_pct":  h2h_b["away_wr"],
        "h2h_home_goals_pg": h2h_b["home_gpg"],
        "h2h_away_goals_pg": h2h_b["away_gpg"],
        "home_adv_league":   _LEAGUE_HOME_ADV.get((league or "").lower(), _DEFAULT_HOME_ADV),
        "elo_diff":          _elo_proxy(
            {"pts_pg": home_10["pts_pg"], "gf_pg": home_10["gf_pg"], "ga_pg": home_10["ga_pg"]},
            {"pts_pg": away_10["pts_pg"], "gf_pg": away_10["gf_pg"], "ga_pg": away_10["ga_pg"]},
        ),
    })

    # Completeness: 1.0 if we have ≥5 home, ≥5 away, ≥3 h2h matches
    completeness_signals.append(min(1.0, home_10["n"] / 5.0))
    completeness_signals.append(min(1.0, away_10["n"] / 5.0))
    completeness_signals.append(min(1.0, h2h_b["n"] / 3.0))
    out["feature_completeness"] = round(sum(completeness_signals) / 3.0, 3)

    return out
