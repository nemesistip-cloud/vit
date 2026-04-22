"""
Module F — Feature Engineering
Transforms raw MatchContext data into a structured, model-ready feature vector.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def engineer_features(
    fixture: Dict,
    standings: Dict,
    injuries: List[Dict],
    odds_data: Optional[Dict],
    recent_form: Dict[str, List[Dict]],
    head_to_head: Dict[str, List[Dict]],
) -> Dict[str, Any]:
    """
    Produce a flat feature dict from all available raw context.

    Returns a dict with the following top-level groups:
        market, form, h2h, injury, standings, derived
    """
    features: Dict[str, Any] = {}

    home_name = fixture.get("home_team", {}).get("name", "")
    away_name = fixture.get("away_team", {}).get("name", "")
    home_ext_id = str(fixture.get("home_team", {}).get("external_id", ""))
    away_ext_id = str(fixture.get("away_team", {}).get("external_id", ""))

    features.update(_market_features(odds_data))
    features.update(_form_features(home_ext_id, away_ext_id, recent_form))
    features.update(_h2h_features(home_name, away_name, head_to_head))
    features.update(_injury_features(home_name, away_name, injuries))
    features.update(_standings_features(home_name, away_name, standings))
    features.update(_derived_features(features))

    return features


def compute_source_quality(features: Dict[str, Any]) -> float:
    """
    Score 0-1 representing data completeness.
    Each feature group contributes equally (20% each).
    """
    checks = [
        features.get("market_overround") is not None,        # market data
        features.get("home_form_points") is not None,         # form data
        features.get("h2h_total_played") is not None,         # h2h data
        features.get("home_injury_count") is not None,        # injury data
        features.get("home_position") is not None,            # standings data
    ]
    return round(sum(checks) / len(checks), 2)


# ---------------------------------------------------------------------------
# Feature group extractors
# ---------------------------------------------------------------------------

def _market_features(odds_data: Optional[Dict]) -> Dict[str, Any]:
    if not odds_data:
        return {}

    vfp = odds_data.get("vig_free_probs", {})
    return {
        "market_home_odds": odds_data.get("home"),
        "market_draw_odds": odds_data.get("draw"),
        "market_away_odds": odds_data.get("away"),
        "market_over25_odds": odds_data.get("over_25"),
        "market_btts_odds": odds_data.get("btts_yes"),
        "market_overround": odds_data.get("overround"),
        "market_bookmaker": odds_data.get("bookmaker"),
        "market_home_prob_vf": vfp.get("home"),
        "market_draw_prob_vf": vfp.get("draw"),
        "market_away_prob_vf": vfp.get("away"),
        "market_over25_prob_vf": vfp.get("over_25"),
        "market_btts_prob_vf": vfp.get("btts_yes"),
    }


def _form_features(
    home_ext_id: str,
    away_ext_id: str,
    recent_form: Dict[str, List[Dict]],
) -> Dict[str, Any]:
    home_matches = recent_form.get(home_ext_id, [])[:5]
    away_matches = recent_form.get(away_ext_id, [])[:5]

    def _form_stats(matches: List[Dict]) -> Dict[str, Any]:
        if not matches:
            return {}
        pts = gf = ga = wins = draws = losses = 0
        for m in matches:
            hg = m.get("home_goals") or 0
            ag = m.get("away_goals") or 0
            outcome = m.get("outcome")
            if outcome == "home":
                pts += 3; wins += 1
            elif outcome == "draw":
                pts += 1; draws += 1
            else:
                losses += 1
            gf += hg; ga += ag
        return {
            "form_points": pts,
            "form_gf": gf,
            "form_ga": ga,
            "form_wins": wins,
            "form_draws": draws,
            "form_losses": losses,
            "form_gd": gf - ga,
            "form_games": len(matches),
        }

    home_stats = _form_stats(home_matches)
    away_stats = _form_stats(away_matches)

    result: Dict[str, Any] = {}
    for k, v in home_stats.items():
        result[f"home_{k}"] = v
    for k, v in away_stats.items():
        result[f"away_{k}"] = v
    return result


def _h2h_features(
    home_name: str,
    away_name: str,
    head_to_head: Dict[str, List[Dict]],
) -> Dict[str, Any]:
    key = f"{home_name}_vs_{away_name}"
    alt_key = f"{away_name}_vs_{home_name}"
    matches = head_to_head.get(key, head_to_head.get(alt_key, []))[:5]

    if not matches:
        return {}

    home_wins = draws = away_wins = 0
    total_goals = btts_count = 0

    for m in matches:
        hg = m.get("home_goals") or 0
        ag = m.get("away_goals") or 0
        outcome = m.get("outcome")
        if outcome == "home":
            home_wins += 1
        elif outcome == "draw":
            draws += 1
        else:
            away_wins += 1
        total_goals += hg + ag
        if hg > 0 and ag > 0:
            btts_count += 1

    total = len(matches)
    return {
        "h2h_total_played": total,
        "h2h_home_wins": home_wins,
        "h2h_draws": draws,
        "h2h_away_wins": away_wins,
        "h2h_home_win_rate": round(home_wins / total, 3) if total else None,
        "h2h_draw_rate": round(draws / total, 3) if total else None,
        "h2h_away_win_rate": round(away_wins / total, 3) if total else None,
        "h2h_avg_goals": round(total_goals / total, 2) if total else None,
        "h2h_btts_rate": round(btts_count / total, 3) if total else None,
    }


def _injury_features(
    home_name: str,
    away_name: str,
    injuries: List[Dict],
) -> Dict[str, Any]:
    if not injuries:
        return {"home_injury_count": 0, "away_injury_count": 0, "home_injury_score": 0.0, "away_injury_score": 0.0}

    def _team_injuries(team_name: str) -> List[Dict]:
        tn = team_name.lower()
        return [
            i for i in injuries
            if tn in str(i.get("team", "")).lower()
            and i.get("status") in ("injured", "doubtful")
        ]

    # Severity weights: injured=1.0, doubtful=0.5
    def _score(inj_list: List[Dict]) -> float:
        score = 0.0
        for i in inj_list:
            score += 1.0 if i.get("status") == "injured" else 0.5
        return round(score, 2)

    home_inj = _team_injuries(home_name)
    away_inj = _team_injuries(away_name)

    return {
        "home_injury_count": len(home_inj),
        "away_injury_count": len(away_inj),
        "home_injury_score": _score(home_inj),
        "away_injury_score": _score(away_inj),
    }


def _standings_features(
    home_name: str,
    away_name: str,
    standings: Dict,
) -> Dict[str, Any]:
    if not standings:
        return {}

    table = standings.get("standings", standings) or {}
    if isinstance(table, list):
        # Some APIs return list of rows
        rows = table
    elif isinstance(table, dict):
        rows = table.get("standings", table.get("table", []))
    else:
        return {}

    if not isinstance(rows, list):
        return {}

    home_row = _find_team_row(home_name, rows)
    away_row = _find_team_row(away_name, rows)

    result: Dict[str, Any] = {}
    if home_row:
        result.update({
            "home_position": home_row.get("position"),
            "home_points": home_row.get("points"),
            "home_gd": home_row.get("goalDifference") or home_row.get("goal_difference"),
            "home_played": home_row.get("playedGames") or home_row.get("played"),
            "home_wins": home_row.get("won"),
            "home_draws": home_row.get("draw"),
            "home_losses": home_row.get("lost"),
        })
    if away_row:
        result.update({
            "away_position": away_row.get("position"),
            "away_points": away_row.get("points"),
            "away_gd": away_row.get("goalDifference") or away_row.get("goal_difference"),
            "away_played": away_row.get("playedGames") or away_row.get("played"),
            "away_wins": away_row.get("won"),
            "away_draws": away_row.get("draw"),
            "away_losses": away_row.get("lost"),
        })

    return result


def _derived_features(features: Dict[str, Any]) -> Dict[str, Any]:
    derived: Dict[str, Any] = {}

    # Position gap (higher = bigger mismatch)
    hp = features.get("home_position")
    ap = features.get("away_position")
    if hp is not None and ap is not None:
        derived["position_gap"] = abs(hp - ap)
        derived["home_is_higher_table"] = 1 if hp < ap else 0

    # Form momentum: pts per game in last 5
    hfg = features.get("home_form_games") or 0
    afg = features.get("away_form_games") or 0
    if hfg:
        derived["home_form_ppg"] = round((features.get("home_form_points") or 0) / hfg, 3)
    if afg:
        derived["away_form_ppg"] = round((features.get("away_form_points") or 0) / afg, 3)

    # Goal threat differential
    hgf = features.get("home_form_gf") or 0
    aga = features.get("away_form_ga") or 0
    agf = features.get("away_form_gf") or 0
    hga = features.get("home_form_ga") or 0
    if hfg and afg:
        derived["home_goal_threat"] = round((hgf / hfg) - (aga / afg), 3)
        derived["away_goal_threat"] = round((agf / afg) - (hga / hfg), 3)

    # Injury handicap ratio
    hi = features.get("home_injury_score") or 0
    ai = features.get("away_injury_score") or 0
    derived["injury_balance"] = round(hi - ai, 2)   # positive = home disadvantaged

    # Home-advantage constant (industry standard ~60% win rate for home)
    derived["home_advantage_factor"] = 0.1

    return derived


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_team_row(team_name: str, rows: List[Dict]) -> Optional[Dict]:
    """Fuzzy-match a team name against standings rows."""
    tn = team_name.lower().strip()
    for row in rows:
        team = row.get("team", {})
        name = (team.get("name") or team.get("shortName") or "").lower().strip()
        if tn in name or name in tn:
            return row
    return None
