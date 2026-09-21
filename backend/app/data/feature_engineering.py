"""
Module F — Feature Engineering (v2.0)
Transforms raw MatchContext data into a structured, model-ready feature vector.

v2.0 additions (Phase 1 — Feature Analytics Upgrade):
  - xG (expected goals) estimated from shot & scoring history
  - Referee statistics (cards, fouls discipline)
  - Rest days since last match (fatigue proxy)
  - Odds movement velocity (opening → closing line drift)
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "2.0"


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
    referee_data: Optional[Dict] = None,
    form_schedule: Optional[Dict[str, List[Dict]]] = None,
) -> Dict[str, Any]:
    """
    Produce a flat feature dict from all available raw context.

    Returns a dict with the following top-level groups:
        market, form, h2h, injury, standings, derived,
        xg, referee, rest, odds_velocity   (v2.0 additions)
    """
    features: Dict[str, Any] = {}

    home_name    = fixture.get("home_team", {}).get("name", "")
    away_name    = fixture.get("away_team", {}).get("name", "")
    home_ext_id  = str(fixture.get("home_team", {}).get("external_id", ""))
    away_ext_id  = str(fixture.get("away_team", {}).get("external_id", ""))
    kickoff_str  = fixture.get("kickoff_time") or fixture.get("date")

    features.update(_market_features(odds_data))
    features.update(_form_features(home_ext_id, away_ext_id, recent_form))
    features.update(_h2h_features(home_name, away_name, head_to_head))
    features.update(_injury_features(home_name, away_name, injuries))
    features.update(_standings_features(home_name, away_name, standings))

    # v2.0 additions
    features.update(_xg_features(home_ext_id, away_ext_id, recent_form))
    features.update(_referee_features(referee_data))
    features.update(_rest_days_features(home_ext_id, away_ext_id, form_schedule, kickoff_str))
    features.update(_odds_velocity_features(odds_data))

    features.update(_derived_features(features))

    return features


def compute_source_quality(features: Dict[str, Any]) -> float:
    """
    Score 0-1 representing data completeness.
    Each feature group contributes equally (14.3% each for 7 groups in v2).
    """
    checks = [
        features.get("market_overround") is not None,          # market
        features.get("home_form_points") is not None,           # form
        features.get("h2h_total_played") is not None,           # h2h
        features.get("home_injury_count") is not None,          # injury
        features.get("home_position") is not None,              # standings
        features.get("home_xg_per_game") is not None,           # xG
        features.get("home_rest_days") is not None,             # rest
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
        "market_home_odds":      odds_data.get("home"),
        "market_draw_odds":      odds_data.get("draw"),
        "market_away_odds":      odds_data.get("away"),
        "market_over25_odds":    odds_data.get("over_25"),
        "market_btts_odds":      odds_data.get("btts_yes"),
        "market_overround":      odds_data.get("overround"),
        "market_bookmaker":      odds_data.get("bookmaker"),
        "market_home_prob_vf":   vfp.get("home"),
        "market_draw_prob_vf":   vfp.get("draw"),
        "market_away_prob_vf":   vfp.get("away"),
        "market_over25_prob_vf": vfp.get("over_25"),
        "market_btts_prob_vf":   vfp.get("btts_yes"),
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
            "form_gf":     gf,
            "form_ga":     ga,
            "form_wins":   wins,
            "form_draws":  draws,
            "form_losses": losses,
            "form_gd":     gf - ga,
            "form_games":  len(matches),
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
    key     = f"{home_name}_vs_{away_name}"
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
        "h2h_total_played":   total,
        "h2h_home_wins":      home_wins,
        "h2h_draws":          draws,
        "h2h_away_wins":      away_wins,
        "h2h_home_win_rate":  round(home_wins / total, 3) if total else None,
        "h2h_draw_rate":      round(draws / total, 3)      if total else None,
        "h2h_away_win_rate":  round(away_wins / total, 3)  if total else None,
        "h2h_avg_goals":      round(total_goals / total, 2) if total else None,
        "h2h_btts_rate":      round(btts_count / total, 3) if total else None,
    }


def _injury_features(
    home_name: str,
    away_name: str,
    injuries: List[Dict],
) -> Dict[str, Any]:
    if not injuries:
        return {
            "home_injury_count": 0,
            "away_injury_count": 0,
            "home_injury_score": 0.0,
            "away_injury_score": 0.0,
        }

    def _team_injuries(team_name: str) -> List[Dict]:
        tn = team_name.lower()
        return [
            i for i in injuries
            if tn in str(i.get("team", "")).lower()
            and i.get("status") in ("injured", "doubtful")
        ]

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
            "home_points":   home_row.get("points"),
            "home_gd":       home_row.get("goalDifference") or home_row.get("goal_difference"),
            "home_played":   home_row.get("playedGames") or home_row.get("played"),
            "home_wins":     home_row.get("won"),
            "home_draws":    home_row.get("draw"),
            "home_losses":   home_row.get("lost"),
        })
    if away_row:
        result.update({
            "away_position": away_row.get("position"),
            "away_points":   away_row.get("points"),
            "away_gd":       away_row.get("goalDifference") or away_row.get("goal_difference"),
            "away_played":   away_row.get("playedGames") or away_row.get("played"),
            "away_wins":     away_row.get("won"),
            "away_draws":    away_row.get("draw"),
            "away_losses":   away_row.get("lost"),
        })

    return result


# ---------------------------------------------------------------------------
# v2.0 Feature group extractors
# ---------------------------------------------------------------------------

def _xg_features(
    home_ext_id: str,
    away_ext_id: str,
    recent_form: Dict[str, List[Dict]],
) -> Dict[str, Any]:
    """
    Estimate xG from recent form matches.

    Uses actual goals scored (home/away) as a proxy for xG when shot data is
    absent.  When a match dict carries explicit 'xg_home' / 'xg_away' fields
    those are preferred.  Also derives attack strength and defence vulnerability
    ratios for use by specialised market models.
    """
    def _xg_stats(matches: List[Dict], team_ext_id: str) -> Dict[str, Any]:
        if not matches:
            return {}

        xg_for_vals:     List[float] = []
        xg_against_vals: List[float] = []
        shots_for_vals:  List[float] = []
        shots_on_vals:   List[float] = []

        for m in matches:
            is_home = str(m.get("home_id", m.get("home_team_id", ""))) == team_ext_id

            # Explicit xG fields (when data provider supplies them)
            xg_h = m.get("xg_home") or m.get("home_xg")
            xg_a = m.get("xg_away") or m.get("away_xg")

            if xg_h is not None and xg_a is not None:
                xg_for     = float(xg_h) if is_home else float(xg_a)
                xg_against = float(xg_a) if is_home else float(xg_h)
            else:
                # Fallback: use actual goals as xG proxy
                hg = float(m.get("home_goals") or 0)
                ag = float(m.get("away_goals") or 0)
                xg_for     = hg if is_home else ag
                xg_against = ag if is_home else hg

            xg_for_vals.append(xg_for)
            xg_against_vals.append(xg_against)

            # Shot metrics (optional)
            shots_h = m.get("shots_home") or m.get("home_shots")
            shots_a = m.get("shots_away") or m.get("away_shots")
            sot_h   = m.get("shots_on_target_home") or m.get("home_shots_on_target")
            sot_a   = m.get("shots_on_target_away") or m.get("away_shots_on_target")

            if shots_h is not None and shots_a is not None:
                shots_for_vals.append(float(shots_h) if is_home else float(shots_a))
            if sot_h is not None and sot_a is not None:
                shots_on_vals.append(float(sot_h) if is_home else float(sot_a))

        n = len(xg_for_vals)
        if n == 0:
            return {}

        xg_for_avg     = round(sum(xg_for_vals) / n, 3)
        xg_against_avg = round(sum(xg_against_vals) / n, 3)
        xg_diff        = round(xg_for_avg - xg_against_avg, 3)

        result: Dict[str, Any] = {
            "xg_per_game":         xg_for_avg,
            "xg_against_per_game": xg_against_avg,
            "xg_diff":             xg_diff,
            "xg_games":            n,
        }

        if shots_for_vals:
            result["shots_per_game"] = round(sum(shots_for_vals) / len(shots_for_vals), 2)
        if shots_on_vals:
            result["shots_on_target_per_game"] = round(sum(shots_on_vals) / len(shots_on_vals), 2)
            if shots_for_vals and sum(shots_for_vals) > 0:
                result["shot_accuracy"] = round(
                    sum(shots_on_vals) / sum(shots_for_vals), 3
                )

        return result

    home_matches = recent_form.get(home_ext_id, [])[:5]
    away_matches = recent_form.get(away_ext_id, [])[:5]

    home_xg = _xg_stats(home_matches, home_ext_id)
    away_xg = _xg_stats(away_matches, away_ext_id)

    result: Dict[str, Any] = {}
    for k, v in home_xg.items():
        result[f"home_{k}"] = v
    for k, v in away_xg.items():
        result[f"away_{k}"] = v

    # Derived xG matchup metrics
    h_xg = home_xg.get("xg_per_game")
    a_xg = away_xg.get("xg_per_game")
    if h_xg is not None and a_xg is not None:
        result["xg_total_expected"] = round(h_xg + a_xg, 3)
        result["xg_dominance"]      = round(h_xg / (h_xg + a_xg), 3) if (h_xg + a_xg) > 0 else 0.5

    return result


def _referee_features(referee_data: Optional[Dict]) -> Dict[str, Any]:
    """
    Extract referee discipline statistics.

    Expected referee_data shape (from external APIs or internal DB):
    {
      "referee_id":       "ref_123",
      "name":             "Michael Oliver",
      "matches_officiated": 38,
      "yellow_cards_per_game": 3.8,
      "red_cards_per_game":    0.12,
      "fouls_per_game":        22.5,
      "home_win_rate":         0.48,
      "penalty_rate_per_game": 0.26,
    }
    """
    if not referee_data:
        return {}

    def _safe(val, default=None):
        try:
            return float(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    yellows = _safe(referee_data.get("yellow_cards_per_game"))
    reds    = _safe(referee_data.get("red_cards_per_game"))
    fouls   = _safe(referee_data.get("fouls_per_game"))
    pen_per = _safe(referee_data.get("penalty_rate_per_game"))
    matches = _safe(referee_data.get("matches_officiated"))
    h_win   = _safe(referee_data.get("home_win_rate"))

    result: Dict[str, Any] = {}
    if yellows  is not None: result["ref_yellows_per_game"]      = yellows
    if reds     is not None: result["ref_reds_per_game"]         = reds
    if fouls    is not None: result["ref_fouls_per_game"]        = fouls
    if pen_per  is not None: result["ref_penalty_rate_per_game"] = pen_per
    if matches  is not None: result["ref_experience_games"]      = matches
    if h_win    is not None: result["ref_home_win_rate"]         = h_win

    # Discipline index: normalised card severity [0, 1]
    if yellows is not None and reds is not None:
        result["ref_discipline_index"] = round(
            min(1.0, (yellows * 1.0 + reds * 3.0) / 10.0), 3
        )

    return result


def _rest_days_features(
    home_ext_id: str,
    away_ext_id: str,
    form_schedule: Optional[Dict[str, List[Dict]]],
    kickoff_str: Optional[str],
) -> Dict[str, Any]:
    """
    Calculate days since each team's last match (rest / fatigue proxy).

    form_schedule: same shape as recent_form but each entry must contain a
    'date' or 'kickoff_time' ISO string for the match.
    kickoff_str: the upcoming fixture's date/time ISO string.
    """
    if not form_schedule or not kickoff_str:
        return {}

    def _parse_dt(s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        for fmt in (
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(s, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        return None

    kickoff_dt = _parse_dt(kickoff_str)
    if kickoff_dt is None:
        return {}

    def _last_match_days(ext_id: str) -> Optional[float]:
        matches = form_schedule.get(ext_id, [])
        latest_dt: Optional[datetime] = None
        for m in matches:
            m_dt = _parse_dt(m.get("date") or m.get("kickoff_time"))
            if m_dt and (latest_dt is None or m_dt > latest_dt):
                latest_dt = m_dt
        if latest_dt is None:
            return None
        days = (kickoff_dt - latest_dt).total_seconds() / 86400.0
        return round(max(0.0, days), 1)

    home_rest = _last_match_days(home_ext_id)
    away_rest = _last_match_days(away_ext_id)

    result: Dict[str, Any] = {}
    if home_rest is not None:
        result["home_rest_days"] = home_rest
        result["home_fatigue_flag"] = 1 if home_rest < 4 else 0   # <4 days = fatigue risk
    if away_rest is not None:
        result["away_rest_days"] = away_rest
        result["away_fatigue_flag"] = 1 if away_rest < 4 else 0
    if home_rest is not None and away_rest is not None:
        result["rest_days_advantage"] = round(home_rest - away_rest, 1)

    return result


def _odds_velocity_features(odds_data: Optional[Dict]) -> Dict[str, Any]:
    """
    Compute odds movement velocity (line drift) from opening → closing odds.

    Opening odds represent the bookmaker's initial probability estimate;
    closing odds reflect sharp-money positioning.  The delta signals
    where informed money has moved, a strong predictor in itself.
    """
    if not odds_data:
        return {}

    def _drift(opening: Optional[float], closing: Optional[float]) -> Optional[float]:
        if opening is None or closing is None:
            return None
        if opening <= 1.0 or closing <= 1.0:
            return None
        # Convert to implied probabilities then measure shift
        p_open  = 1.0 / opening
        p_close = 1.0 / closing
        return round(p_close - p_open, 4)   # positive = odds shortened (became favourite)

    o_home = odds_data.get("opening_home")   or odds_data.get("open_home")
    o_draw = odds_data.get("opening_draw")   or odds_data.get("open_draw")
    o_away = odds_data.get("opening_away")   or odds_data.get("open_away")
    c_home = odds_data.get("home")           or odds_data.get("closing_home")
    c_draw = odds_data.get("draw")           or odds_data.get("closing_draw")
    c_away = odds_data.get("away")           or odds_data.get("closing_away")

    result: Dict[str, Any] = {}

    dh = _drift(o_home, c_home)
    dd = _drift(o_draw, c_draw)
    da = _drift(o_away, c_away)

    if dh is not None: result["odds_drift_home"] = dh
    if dd is not None: result["odds_drift_draw"] = dd
    if da is not None: result["odds_drift_away"] = da

    # Market velocity: absolute total movement
    drifts = [d for d in (dh, dd, da) if d is not None]
    if drifts:
        result["odds_velocity_total"] = round(sum(abs(d) for d in drifts), 4)

    # Strong steam move flag (≥5% implied probability shift on one side)
    if dh is not None: result["steam_home"] = 1 if dh >  0.05 else 0
    if da is not None: result["steam_away"] = 1 if da >  0.05 else 0

    return result


def _derived_features(features: Dict[str, Any]) -> Dict[str, Any]:
    derived: Dict[str, Any] = {}

    # Position gap (higher = bigger mismatch)
    hp = features.get("home_position")
    ap = features.get("away_position")
    if hp is not None and ap is not None:
        derived["position_gap"]          = abs(hp - ap)
        derived["home_is_higher_table"]  = 1 if hp < ap else 0

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
    derived["injury_balance"] = round(hi - ai, 2)

    # Home-advantage constant (industry standard ~60% win rate for home)
    derived["home_advantage_factor"] = 0.1

    # xG-based attack/defence balance (v2.0)
    h_xg_for = features.get("home_xg_per_game")
    a_xg_for = features.get("away_xg_per_game")
    h_xg_ag  = features.get("home_xg_against_per_game")
    a_xg_ag  = features.get("away_xg_against_per_game")

    if h_xg_for is not None and a_xg_ag is not None:
        derived["xg_attack_vs_defence_home"] = round(h_xg_for - a_xg_ag, 3)
    if a_xg_for is not None and h_xg_ag is not None:
        derived["xg_attack_vs_defence_away"] = round(a_xg_for - h_xg_ag, 3)

    # Composite fatigue differential (v2.0)
    h_rest = features.get("home_rest_days")
    a_rest = features.get("away_rest_days")
    if h_rest is not None and a_rest is not None:
        derived["rest_advantage_home"] = 1 if h_rest > a_rest + 1 else (
            -1 if a_rest > h_rest + 1 else 0
        )

    # Poisson lambda estimates for total goals (uses xG when available)
    lambda_h = h_xg_for if h_xg_for is not None else (
        features.get("home_form_gf", 0) / max(hfg, 1)
    )
    lambda_a = a_xg_for if a_xg_for is not None else (
        features.get("away_form_gf", 0) / max(afg, 1)
    )
    derived["lambda_home"] = round(float(lambda_h), 3)
    derived["lambda_away"] = round(float(lambda_a), 3)

    # Over 2.5 goals probability via Poisson (Dixon-Coles style)
    total_lambda = float(lambda_h) + float(lambda_a)
    if total_lambda > 0:
        p_over25 = 1.0 - _poisson_cdf(total_lambda, 2)
        derived["poisson_over25_prob"] = round(p_over25, 4)
        # BTTS probability: P(home ≥ 1) * P(away ≥ 1)
        p_home_scores = 1.0 - math.exp(-float(lambda_h))
        p_away_scores = 1.0 - math.exp(-float(lambda_a))
        derived["poisson_btts_prob"] = round(p_home_scores * p_away_scores, 4)

    return derived


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _poisson_cdf(lam: float, k: int) -> float:
    """P(X ≤ k) for Poisson(lam)."""
    total = 0.0
    fact = 1.0
    e_lam = math.exp(-lam)
    lam_pow = 1.0
    for i in range(k + 1):
        if i > 0:
            fact *= i
            lam_pow *= lam
        total += e_lam * lam_pow / fact
    return total


def _find_team_row(team_name: str, rows: List[Dict]) -> Optional[Dict]:
    """Fuzzy-match a team name against standings rows."""
    tn = team_name.lower().strip()
    for row in rows:
        team = row.get("team", {})
        name = (team.get("name") or team.get("shortName") or "").lower().strip()
        if tn in name or name in tn:
            return row
    return None
