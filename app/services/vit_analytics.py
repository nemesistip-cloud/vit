# app/services/vit_analytics.py
# VIT Analytics utility functions used by AI agents
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def synthetic_odds(home_prob: float, draw_prob: float, away_prob: float,
                   margin: float = 0.05) -> Dict[str, float]:
    """Convert ML probabilities to decimal odds with a small book margin."""
    def _to_odds(p: float) -> float:
        if p <= 0:
            return 99.0
        raw = 1.0 / p
        return round(raw * (1 - margin), 2)

    return {
        "home": _to_odds(home_prob),
        "draw": _to_odds(draw_prob),
        "away": _to_odds(away_prob),
    }


def detect_probability_drift(
    prev_probs: Dict[int, Dict],
    curr_probs: Dict[int, Dict],
    threshold: float = 0.05,
) -> List[Dict[str, Any]]:
    """Detect significant shifts in ML probability between two snapshots."""
    anomalies: List[Dict[str, Any]] = []
    for match_id, curr in curr_probs.items():
        prev = prev_probs.get(match_id)
        if not prev:
            continue
        for key in ("home_p", "draw_p", "away_p"):
            delta = abs(curr.get(key, 0) - prev.get(key, 0))
            if delta >= threshold:
                anomalies.append({
                    "match_id": match_id,
                    "home_team": curr.get("home_team", ""),
                    "away_team": curr.get("away_team", ""),
                    "key": key,
                    "prev": prev.get(key, 0),
                    "curr": curr.get(key, 0),
                    "delta": round(delta, 4),
                })
    return anomalies


async def get_team_form(team: str, db: Any, n: int = 5) -> Dict[str, Any]:
    """Get the recent form for a team from settled matches."""
    try:
        from sqlalchemy import select, or_
        from app.db.models import Match

        result = await db.execute(
            select(Match)
            .where(
                or_(Match.home_team == team, Match.away_team == team),
                Match.status == "settled",
            )
            .order_by(Match.kickoff_time.desc())
            .limit(n)
        )
        matches = list(result.scalars().all())

        wins = draws = losses = goals_for = goals_against = 0
        results_str = []
        for m in matches:
            home_score = m.home_score or 0
            away_score = m.away_score or 0
            if m.home_team == team:
                gf, ga = home_score, away_score
            else:
                gf, ga = away_score, home_score
            goals_for += gf
            goals_against += ga
            if gf > ga:
                wins += 1
                results_str.append("W")
            elif gf == ga:
                draws += 1
                results_str.append("D")
            else:
                losses += 1
                results_str.append("L")

        return {
            "team": team,
            "matches": len(matches),
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "form_string": "".join(results_str),
        }
    except Exception as e:
        logger.debug("[vit_analytics] get_team_form error for %s: %s", team, e)
        return {"team": team, "matches": 0, "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0, "form_string": ""}


async def get_match_context(match: Any, pred: Any, db: Any) -> Dict[str, Any]:
    """Build a rich SCIE context dict for a match."""
    try:
        home_form = await get_team_form(match.home_team, db, n=5)
        away_form = await get_team_form(match.away_team, db, n=5)

        home_prob = float(pred.home_prob) if pred and pred.home_prob else 0.4
        draw_prob = float(pred.draw_prob) if pred and pred.draw_prob else 0.25
        away_prob = float(pred.away_prob) if pred and pred.away_prob else 0.35

        odds = synthetic_odds(home_prob, draw_prob, away_prob)

        return {
            "match_id": match.id,
            "home_team": match.home_team,
            "away_team": match.away_team,
            "league": getattr(match, "league", "unknown"),
            "kickoff": match.kickoff_time.isoformat() if match.kickoff_time else None,
            "home_prob": home_prob,
            "draw_prob": draw_prob,
            "away_prob": away_prob,
            "synthetic_odds": odds,
            "home_form": home_form,
            "away_form": away_form,
        }
    except Exception as e:
        logger.debug("[vit_analytics] get_match_context error: %s", e)
        return {
            "match_id": getattr(match, "id", 0),
            "home_team": getattr(match, "home_team", ""),
            "away_team": getattr(match, "away_team", ""),
            "league": getattr(match, "league", "unknown"),
            "kickoff": None,
            "home_prob": 0.4, "draw_prob": 0.25, "away_prob": 0.35,
            "synthetic_odds": {"home": 2.5, "draw": 4.0, "away": 2.85},
            "home_form": {}, "away_form": {},
        }


def build_scout_prompt(ctx: Dict[str, Any]) -> str:
    """Build an AI scout prompt from SCIE context."""
    home = ctx.get("home_team", "Home")
    away = ctx.get("away_team", "Away")
    league = str(ctx.get("league", "")).replace("_", " ").title()
    ko = (ctx.get("kickoff") or "")[:16]
    hp = ctx.get("home_prob", 0.4)
    dp = ctx.get("draw_prob", 0.25)
    ap = ctx.get("away_prob", 0.35)
    odds = ctx.get("synthetic_odds", {})

    hf = ctx.get("home_form", {})
    af = ctx.get("away_form", {})

    def _form_line(f: dict) -> str:
        if not f or not f.get("matches"):
            return "No recent data"
        return (f"{f.get('form_string','?')} — "
                f"W{f.get('wins',0)} D{f.get('draws',0)} L{f.get('losses',0)} "
                f"GF{f.get('goals_for',0)} GA{f.get('goals_against',0)}")

    return f"""You are an elite football scout. Write a detailed pre-match analytics brief.

Match: {home} vs {away}
League: {league}
Kickoff: {ko} UTC
ML Ensemble: Home {hp*100:.1f}% | Draw {dp*100:.1f}% | Away {ap*100:.1f}%
VIT Market Odds: {home} {odds.get('home',2.5)} | Draw {odds.get('draw',4.0)} | {away} {odds.get('away',2.85)}
{home} Recent Form: {_form_line(hf)}
{away} Recent Form: {_form_line(af)}

Return ONLY a JSON object (no markdown fences, no extra text):
{{
  "headline": "one punchy line summarising the key narrative",
  "home_form": "3-sentence form assessment",
  "away_form": "3-sentence form assessment",
  "key_factors": ["factor 1", "factor 2", "factor 3", "factor 4"],
  "tactical_note": "2-sentence tactical matchup insight",
  "value_pick": "specific bet recommendation with brief justification",
  "risk_level": "LOW|MEDIUM|HIGH",
  "confidence": 0.0
}}"""
