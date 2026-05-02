"""app/services/openai_insights.py — OpenAI GPT match insights"""

import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL   = "gpt-4o-mini"


def _no_key() -> dict:
    return {
        "available": False,
        "source": "openai",
        "error": "OPENAI_API_KEY not configured — add it in Admin → API Keys",
        "home_prob": None, "draw_prob": None, "away_prob": None, "confidence": None,
        "summary": None, "key_factors": [], "value_assessment": None,
        "risk_level": None, "insight_tags": [],
    }


def _build_prompt(
    home_team, away_team, league, home_prob, draw_prob, away_prob,
    over_25_prob, btts_prob, bet_side, edge, entry_odds, confidence
) -> str:
    league_label = league.replace("_", " ").title()
    ou   = f"- Over 2.5 Goals: {over_25_prob*100:.1f}%" if over_25_prob is not None else ""
    btts = f"- Both Teams to Score: {btts_prob*100:.1f}%" if btts_prob is not None else ""
    return f"""You are a sharp football betting analyst. Give an independent probability assessment and tactical breakdown.

Match: {home_team} vs {away_team} | League: {league_label}

ML Ensemble output:
- Home Win: {home_prob*100:.1f}% | Draw: {draw_prob*100:.1f}% | Away Win: {away_prob*100:.1f}%
{ou}
{btts}
Value analysis: Side={str(bet_side).upper()}, Edge={edge*100:.2f}%, Odds={f"{entry_odds:.2f}" if entry_odds else "N/A"}, Confidence={confidence*100:.0f}%

Return ONLY valid JSON (no markdown fences):
{{
  "home_prob": 0.00,
  "draw_prob": 0.00,
  "away_prob": 0.00,
  "confidence": 0.00,
  "summary": "2-3 sentence analysis",
  "key_factors": ["factor 1", "factor 2", "factor 3"],
  "value_assessment": "1-2 sentences on value",
  "risk_level": "LOW",
  "insight_tags": ["tag1", "tag2"]
}}

Probabilities must sum to 1.0. risk_level: LOW | MEDIUM | HIGH."""


async def generate_match_insights(
    home_team: str, away_team: str, league: str,
    home_prob: float, draw_prob: float, away_prob: float,
    over_25_prob: Optional[float] = None, btts_prob: Optional[float] = None,
    bet_side: Optional[str] = None, edge: float = 0.0,
    entry_odds: Optional[float] = None, confidence: float = 0.5,
) -> dict:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return _no_key()

    prompt = _build_prompt(
        home_team, away_team, league, home_prob, draw_prob, away_prob,
        over_25_prob, btts_prob, bet_side, edge, entry_odds, confidence
    )

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.post(
                OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 512,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        raw = data["choices"][0]["message"]["content"].strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)

        home_p = float(parsed.get("home_prob", home_prob))
        draw_p = float(parsed.get("draw_prob", draw_prob))
        away_p = float(parsed.get("away_prob", away_prob))
        total  = home_p + draw_p + away_p
        if total > 0 and abs(total - 1.0) > 0.01:
            home_p /= total
            draw_p /= total
            away_p /= total

        return {
            "available": True,
            "source": "openai",
            "model": OPENAI_MODEL,
            "home_prob": round(home_p, 4),
            "draw_prob": round(draw_p, 4),
            "away_prob": round(away_p, 4),
            "confidence": float(parsed.get("confidence", confidence)),
            "summary": parsed.get("summary", ""),
            "key_factors": parsed.get("key_factors", []),
            "value_assessment": parsed.get("value_assessment", ""),
            "risk_level": parsed.get("risk_level", "MEDIUM"),
            "insight_tags": parsed.get("insight_tags", []),
        }

    except json.JSONDecodeError as exc:
        logger.error(f"OpenAI response JSON parse failed: {exc}")
        return {
            "available": False, "source": "openai", "error": f"JSON parse error: {exc}",
            "home_prob": None, "draw_prob": None, "away_prob": None, "confidence": None,
            "summary": None, "key_factors": [], "value_assessment": None,
            "risk_level": None, "insight_tags": [],
        }
    except httpx.HTTPStatusError as exc:
        logger.error(f"OpenAI HTTP error {exc.response.status_code}: {exc.response.text[:200]}")
        return {
            "available": False, "source": "openai",
            "error": f"HTTP {exc.response.status_code}",
            "home_prob": None, "draw_prob": None, "away_prob": None, "confidence": None,
            "summary": None, "key_factors": [], "value_assessment": None,
            "risk_level": None, "insight_tags": [],
        }
    except Exception as exc:
        logger.error(f"OpenAI insights failed: {exc}", exc_info=True)
        return {
            "available": False, "source": "openai", "error": str(exc),
            "home_prob": None, "draw_prob": None, "away_prob": None, "confidence": None,
            "summary": None, "key_factors": [], "value_assessment": None,
            "risk_level": None, "insight_tags": [],
        }
