"""app/services/scie.py — Statistical Contextual Intelligence Engine (SCIE).

Zero-API fallback data layer. Provides statistically reasonable defaults
when all external APIs are unavailable. Used by the multi-AI dispatcher
and prediction engine as a last-resort data source.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# League-specific baseline statistics (from historical averages)
LEAGUE_BASELINES: dict[str, dict] = {
    "premier_league":     {"home_win": 0.46, "draw": 0.26, "away_win": 0.28, "avg_goals": 2.72, "btts": 0.52},
    "la_liga":            {"home_win": 0.48, "draw": 0.26, "away_win": 0.26, "avg_goals": 2.58, "btts": 0.50},
    "serie_a":            {"home_win": 0.46, "draw": 0.28, "away_win": 0.26, "avg_goals": 2.51, "btts": 0.50},
    "bundesliga":         {"home_win": 0.46, "draw": 0.25, "away_win": 0.29, "avg_goals": 2.97, "btts": 0.56},
    "ligue_1":            {"home_win": 0.47, "draw": 0.27, "away_win": 0.26, "avg_goals": 2.62, "btts": 0.51},
    "champions_league":   {"home_win": 0.44, "draw": 0.24, "away_win": 0.32, "avg_goals": 2.89, "btts": 0.53},
    "europa_league":      {"home_win": 0.43, "draw": 0.25, "away_win": 0.32, "avg_goals": 2.74, "btts": 0.51},
    "default":            {"home_win": 0.45, "draw": 0.26, "away_win": 0.29, "avg_goals": 2.65, "btts": 0.51},
}


def _league_key(league: str) -> str:
    """Normalize league name to a baseline key."""
    league = (league or "").lower().replace(" ", "_").replace("-", "_")
    for k in LEAGUE_BASELINES:
        if k in league or league in k:
            return k
    return "default"


def _team_strength_offset(team_name: str) -> float:
    """
    Deterministic pseudo-random offset based on team name hash.
    Range: -0.04 to +0.04. Provides minor differentiation between teams
    without needing real team rating data.
    """
    h = int(hashlib.md5(team_name.lower().encode()).hexdigest(), 16)
    return ((h % 81) - 40) / 1000.0


def get_match_priors(
    home_team: str,
    away_team: str,
    league: str = "default",
) -> dict[str, Any]:
    """
    Return statistically grounded prior probabilities for a match.
    These are not predictions — they are baseline priors for Bayesian updating.

    Returns:
        home_prob, draw_prob, away_prob (sum to 1.0)
        over_25_prob, btts_prob
        avg_goals
        source: "scie"
        confidence: 0.35 (low — these are priors only)
    """
    key = _league_key(league)
    base = LEAGUE_BASELINES[key]

    home_offset = _team_strength_offset(home_team)
    away_offset = _team_strength_offset(away_team)

    raw_home = base["home_win"] + home_offset - away_offset
    raw_away = base["away_win"] + away_offset - home_offset
    raw_draw = base["draw"]

    # Normalize to sum to 1.0
    total = raw_home + raw_draw + raw_away
    home_prob = max(0.05, min(0.90, raw_home / total))
    away_prob = max(0.05, min(0.90, raw_away / total))
    draw_prob = max(0.05, 1.0 - home_prob - away_prob)

    # Re-normalize after clipping
    s = home_prob + draw_prob + away_prob
    home_prob /= s
    draw_prob /= s
    away_prob /= s

    avg_goals = base["avg_goals"]
    # Poisson approximation: P(goals > 2.5) ≈ 1 - P(0,1,2 goals)
    import math
    lam = avg_goals
    p_under = sum(math.exp(-lam) * (lam ** k) / math.factorial(k) for k in range(3))
    over_25 = round(1.0 - p_under, 4)

    return {
        "available":    True,
        "source":       "scie",
        "label":        "VIT Statistical Engine",
        "home_prob":    round(home_prob, 4),
        "draw_prob":    round(draw_prob, 4),
        "away_prob":    round(away_prob, 4),
        "over_25_prob": over_25,
        "btts_prob":    round(base["btts"], 4),
        "avg_goals":    avg_goals,
        "confidence":   0.35,
        "summary": (
            f"Statistical prior for {home_team} vs {away_team} in {league.replace('_', ' ').title()}. "
            f"Based on {key.replace('_', ' ').title()} historical averages. "
            f"No external data available — treat as baseline only."
        ),
        "key_factors": [
            f"Home advantage factored: {key.replace('_', ' ').title()} base rate {base['home_win']*100:.0f}%",
            f"Over 2.5 goals probability: {over_25*100:.1f}%",
            f"BTTS probability: {base['btts']*100:.1f}%",
        ],
        "value_assessment": "No value assessment available — statistical prior only",
        "risk_level":       "high",
        "insight_tags":     ["scie", "statistical_prior", "fallback"],
    }


async def generate_match_insights(
    home_team: str,
    away_team: str,
    league: str = "default",
    home_prob: float = 0.33,
    draw_prob: float = 0.33,
    away_prob: float = 0.34,
    over_25_prob: Optional[float] = None,
    btts_prob: Optional[float] = None,
    bet_side: Optional[str] = None,
    edge: float = 0.0,
    entry_odds: Optional[float] = None,
    confidence: float = 0.5,
) -> dict[str, Any]:
    """Async wrapper — returns SCIE statistical priors as AI insight fallback."""
    logger.info("[scie] Generating fallback priors for %s vs %s (%s)", home_team, away_team, league)
    return get_match_priors(home_team, away_team, league)
