"""app/services/gemini_insights.py — Google Gemini match insights"""

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
    "risk_level": None,
    "insight_tags": [],
    "error": None,
}


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
    """Call Google Gemini to generate tactical insights for a prediction."""

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _no_key()

    league_label = league.replace("_", " ").title()
    ou_line = f"- Over 2.5 Goals: {over_25_prob * 100:.1f}%" if over_25_prob is not None else ""
    btts_line = f"- Both Teams to Score: {btts_prob * 100:.1f}%" if btts_prob is not None else ""
    odds_str = f"{entry_odds:.2f}" if entry_odds else "N/A"
    bet_label = (bet_side or "none").upper()

    prompt = f"""You are a professional football betting analyst. Analyse this ML prediction and provide concise, insightful commentary.

Match: {home_team} vs {away_team}
League: {league_label}

ML Ensemble Output:
- Home Win: {home_prob * 100:.1f}%
- Draw: {draw_prob * 100:.1f}%
- Away Win: {away_prob * 100:.1f}%
{ou_line}
{btts_line}

Value Analysis:
- Recommended Side: {bet_label}
- Estimated Edge: {edge * 100:.2f}%
- Market Odds: {odds_str}
- Model Confidence: {confidence * 100:.0f}%

Respond with ONLY valid JSON — no markdown, no code fences:
{{
  "summary": "2-3 sentence tactical overview of this fixture based on the predictions",
  "key_factors": ["brief factor 1", "brief factor 2", "brief factor 3"],
  "value_assessment": "1-2 sentences on whether this bet represents good value",
  "risk_level": "LOW",
  "insight_tags": ["tag1", "tag2", "tag3"]
}}

risk_level must be one of: LOW, MEDIUM, HIGH.
insight_tags should be 2-4 short labels like "Strong Home Form", "Low Scoring Expected", "Value Bet", "High Risk".
Be specific and concise. No generic statements."""

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{GEMINI_API_URL}?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.6,
                        "maxOutputTokens": 600,
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
            raw_text = raw_text.split("\n", 1)[-1]
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("```", 1)[0]

        parsed = json.loads(raw_text.strip())

        return {
            "available": True,
            "summary": parsed.get("summary", ""),
            "key_factors": parsed.get("key_factors", []),
            "value_assessment": parsed.get("value_assessment", ""),
            "risk_level": parsed.get("risk_level", "MEDIUM"),
            "insight_tags": parsed.get("insight_tags", []),
            "error": None,
        }

    except json.JSONDecodeError:
        # Return raw text as summary if JSON parse fails
        raw = locals().get("raw_text", "")
        return {
            "available": True,
            "summary": raw[:400] if raw else "AI analysis unavailable",
            "key_factors": [],
            "value_assessment": "",
            "risk_level": "MEDIUM",
            "insight_tags": [],
            "error": None,
        }
    except Exception as exc:
        logger.error(f"Gemini insights error: {exc}")
        return {**_EMPTY, "error": str(exc)}
