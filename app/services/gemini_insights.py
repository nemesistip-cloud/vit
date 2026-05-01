"""app/services/gemini_insights.py — Google Gemini match insights (v4.7.5)

Analyst roles baked into the system prompt:
  • Tactical Analyst  — assesses team dynamics and match setup
  • Value Analyst     — evaluates edge vs. market price
  • Risk Analyst      — flags volatility and confidence level
  • Model Interpreter — translates ensemble probabilities into narrative
"""

import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/gemini-1.5-flash:generateContent"
)

_EMPTY = {
    "available": False,
    "summary": None,
    "key_factors": [],
    "value_assessment": None,
    "recommendation": None,
    "risk_level": None,
    "insight_tags": [],
    "error": None,
}

SYSTEM_PROMPT = """You are a senior football intelligence analyst at VIT Sports Network.
You combine four specialised lenses when assessing a fixture:

1. TACTICAL ANALYST — How will this match play out tactically? Which team has the structural advantage?
2. VALUE ANALYST — Does the model-derived probability represent an edge over the bookmaker price?
3. RISK ANALYST — How confident should the bettor be? What could invalidate this prediction?
4. MODEL INTERPRETER — What are the key signals the 12-model ML ensemble is picking up?

Always be specific. Never write generic statements like "the home team is strong". Reference probability numbers.
"""


def _no_key() -> dict:
    return {**_EMPTY, "error": "GEMINI_API_KEY not configured — add it in Admin → API Keys"}


async def generate_match_insights(
    home_team: str,
    away_team: str,
    league: str,
    home_prob: float,
    draw_prob: float,
    away_prob: float,
    over_25_prob: Optional[float] = None,
    btts_prob: Optional[float] = None,
    bet_side: Optional[str] = None,
    edge: float = 0.0,
    entry_odds: Optional[float] = None,
    confidence: float = 0.5,
) -> dict:
    """Call Google Gemini to generate multi-role tactical insights for a prediction."""

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _no_key()

    league_label = league.replace("_", " ").title()
    ou_line   = f"- Over 2.5 Goals probability: {over_25_prob * 100:.1f}%" if over_25_prob is not None else ""
    btts_line = f"- Both Teams to Score probability: {btts_prob * 100:.1f}%" if btts_prob is not None else ""
    odds_str  = f"{entry_odds:.2f}" if entry_odds else "N/A"
    bet_label = (bet_side or "none").upper()
    edge_pct  = edge * 100

    # Derive implied probability from market odds for value context
    implied_prob = (1 / entry_odds) if entry_odds and entry_odds > 1 else None
    implied_line = f"- Market implied prob: {implied_prob * 100:.1f}%" if implied_prob else ""
    model_prob_for_side = {"HOME": home_prob, "DRAW": draw_prob, "AWAY": away_prob}.get(bet_label, None)
    model_line = f"- Model probability for recommended side: {model_prob_for_side * 100:.1f}%" if model_prob_for_side else ""

    user_prompt = f"""Fixture: {home_team} vs {away_team}  |  League: {league_label}

=== ML ENSEMBLE OUTPUT (12-model weighted average) ===
- Home Win: {home_prob * 100:.1f}%
- Draw: {draw_prob * 100:.1f}%
- Away Win: {away_prob * 100:.1f}%
{ou_line}
{btts_line}

=== VALUE ANALYSIS ===
- Recommended Side: {bet_label}
{model_line}
- Market Odds: {odds_str}
{implied_line}
- Estimated Edge: {edge_pct:.2f}%  (positive = value bet)
- Ensemble Confidence: {confidence * 100:.0f}%

Apply your four analytical lenses and respond with ONLY valid JSON (no markdown, no code fences):
{{
  "summary": "2-3 sentence tactical overview specific to this fixture and the ensemble output",
  "key_factors": [
    "Factor 1 from tactical analysis",
    "Factor 2 from value analysis",
    "Factor 3 from risk analysis",
    "Factor 4 from model interpretation"
  ],
  "value_assessment": "1-2 sentences: is this edge genuine? Is the model vs market discrepancy meaningful?",
  "recommendation": "One clear action sentence starting with BET / SKIP / MONITOR: e.g. 'BET HOME at {odds_str} — {edge_pct:.1f}% model edge exceeds threshold'",
  "risk_level": "MEDIUM",
  "insight_tags": ["tag1", "tag2", "tag3"]
}}

Rules:
- risk_level: LOW (confidence≥70%, edge>3%), MEDIUM (moderate), HIGH (low confidence or small edge)
- insight_tags: 2-5 short capitalised labels e.g. "Value Bet", "Home Dominant", "Low Scoring Expected", "Backing Away", "High Variance"
- recommendation must start with BET, SKIP, or MONITOR
- Be concise and specific. Reference probability numbers."""

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.post(
                f"{GEMINI_API_URL}?key={api_key}",
                json={
                    "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": [{"parts": [{"text": user_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.55,
                        "maxOutputTokens": 800,
                        "responseMimeType": "application/json",
                    },
                },
                headers={"Content-Type": "application/json"},
            )

        if resp.status_code in (401, 403):
            return {**_EMPTY, "error": "Invalid Gemini API key — check Admin → API Keys"}
        if resp.status_code == 429:
            return {**_EMPTY, "error": "Gemini API rate limit reached — try again shortly"}
        if not resp.is_success:
            return {**_EMPTY, "error": f"Gemini API returned HTTP {resp.status_code}"}

        data = resp.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = "\n".join(raw_text.split("\n")[1:])
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("```", 1)[0]

        parsed = json.loads(raw_text.strip())

        risk = str(parsed.get("risk_level", "MEDIUM")).upper()
        if risk not in {"LOW", "MEDIUM", "HIGH"}:
            risk = "MEDIUM"

        return {
            "available": True,
            "summary": parsed.get("summary", ""),
            "key_factors": parsed.get("key_factors", [])[:5],
            "value_assessment": parsed.get("value_assessment", ""),
            "recommendation": parsed.get("recommendation", ""),
            "risk_level": risk,
            "insight_tags": parsed.get("insight_tags", [])[:5],
            "home_prob": home_prob,
            "draw_prob": draw_prob,
            "away_prob": away_prob,
            "confidence": confidence,
            "error": None,
        }

    except json.JSONDecodeError:
        raw = locals().get("raw_text", "")
        return {
            "available": True,
            "summary": raw[:500] if raw else "AI analysis unavailable",
            "key_factors": [],
            "value_assessment": "",
            "recommendation": "",
            "risk_level": "MEDIUM",
            "insight_tags": [],
            "home_prob": home_prob,
            "draw_prob": draw_prob,
            "away_prob": away_prob,
            "confidence": confidence,
            "error": "JSON parse failed — raw text returned as summary",
        }
    except Exception as exc:
        logger.error(f"Gemini insights error: {exc}")
        return {**_EMPTY, "error": str(exc)}
