# app/services/vit_analytics.py
# VIT Analytics utility functions used by AI agents
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, or_, and_, desc

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

async def get_match_context(match: Any, pred: Any, db: Any) -> Dict[str, Any]:
    """Build enriched pre-match context for scouting/AI analysis."""
    hp = float(pred.home_prob) if pred and pred.home_prob else 0.34
    dp = float(pred.draw_prob) if pred and pred.draw_prob else 0.33
    ap = float(pred.away_prob) if pred and pred.away_prob else 0.33

    # ── Mock form logic for context ──
    # In a real scenario, we would query historical matches here.
    return {
        "home_team": match.home_team,
        "away_team": match.away_team,
        "league": match.league,
        "kickoff": match.kickoff_time.isoformat() if match.kickoff_time else None,
        "home_prob": hp,
        "draw_prob": dp,
        "away_prob": ap,
        "synthetic_odds": synthetic_odds(hp, dp, ap),
        "home_form": {"form_string": "WWDWL", "wins": 3, "draws": 1, "losses": 1, "goals_for": 8, "goals_against": 4},
        "away_form": {"form_string": "LDWWL", "wins": 2, "draws": 1, "losses": 2, "goals_for": 6, "goals_against": 7},
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
            # Mock fallback if no real matches passed
            if f.get("form_string"):
                 return (f"{f.get('form_string','?')} — "
                        f"W{f.get('wins',0)} D{f.get('draws',0)} L{f.get('losses',0)} "
                        f"GF{f.get('goals_for',0)} GA{f.get('goals_against',0)}")
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
  "key_factors": ["Tactical Observation 1", "Tactical Observation 2", "Tactical Observation 3", "Tactical Observation 4"],
  "tactical_note": "Specific tactical matchup insight (e.g. wing play vs narrow defense)",
  "value_pick": "specific bet recommendation with brief justification",
  "risk_level": "LOW|MEDIUM|HIGH",
  "confidence": 0.0
}}"""
