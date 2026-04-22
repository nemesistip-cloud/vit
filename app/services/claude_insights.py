"""app/services/claude_insights.py — Anthropic Claude match insights"""

import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL   = "claude-3-haiku-20240307"


def _no_key() -> dict:
    return {
        "available": False,
        "source": "claude",
        "error": "ANTHROPIC_API_KEY not configured — add it in Admin → API Keys",
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
    return f"""You are a professional football analyst. Analyse this match and give your independent probability assessment plus tactical insights.

Match: {home_team} vs {away_team} | League: {league_label}

ML Ensemble (our model):
- Home Win: {home_prob*100:.1f}% | Draw: {draw_prob*100:.1f}% | Away Win: {away_prob*100:.1f}%
{ou}
{btts}
Value: Side={str(bet_side).upper()}, Edge={edge*100:.2f}%, Odds={f"{entry_odds:.2f}" if entry_odds else "N/A"}, Confidence={confidence*100:.0f}%

Respond with ONLY valid JSON (no markdown):
{{
  "home_prob": 0.00,
  "draw_prob": 0.00,
  "away_prob": 0.00,
  "confidence": 0.00,
  "summary": "2-3 sentence tactical overview",
  "key_factors": ["factor 1", "factor 2", "factor 3"],
  "value_assessment": "1-2 sentences on bet value",
  "risk_level": "LOW",
  "insight_tags": ["tag1", "tag2"]
}}

home_prob + draw_prob + away_prob must sum to 1.0.
risk_level: LOW | MEDIUM | HIGH."""


async def generate_match_insights(
    home_team: str, away_team: str, league: str,
    home_prob: float, draw_prob: float, away_prob: float,
    over_25_prob: Optional[float] = None, btts_prob: Optional[float] = None,
    bet_side: Optional[str] = None, edge: float = 0.0,
    entry_odds: Optional[float] = None, confidence: float = 0.5,
) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return _no_key()

    prompt = _build_prompt(
        home_team, away_team, league, home_prob, draw_prob, away_prob,
        over_25_prob, btts_prob, bet_side, edge, entry_odds, confidence
    )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                CLAUDE_API_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": 600,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )

        if resp.status_code in (401, 403):
            return {**_no_key(), "error": "Invalid Anthropic API key"}
        if resp.status_code == 429:
            return {**_no_key(), "error": "Claude rate limit — try again shortly"}
        if not resp.is_success:
            return {**_no_key(), "error": f"Claude API returned HTTP {resp.status_code}"}

        raw = resp.json()["content"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]

        parsed = json.loads(raw.strip())
        return {
            "available": True, "source": "claude",
            "home_prob": float(parsed.get("home_prob", home_prob)),
            "draw_prob": float(parsed.get("draw_prob", draw_prob)),
            "away_prob": float(parsed.get("away_prob", away_prob)),
            "confidence": float(parsed.get("confidence", 0.7)),
            "summary": parsed.get("summary", ""),
            "key_factors": parsed.get("key_factors", []),
            "value_assessment": parsed.get("value_assessment", ""),
            "risk_level": parsed.get("risk_level", "MEDIUM"),
            "insight_tags": parsed.get("insight_tags", []),
            "error": None,
        }

    except json.JSONDecodeError:
        raw_text = locals().get("raw", "")
        return {
            "available": True, "source": "claude",
            "home_prob": home_prob, "draw_prob": draw_prob, "away_prob": away_prob,
            "confidence": 0.7, "summary": raw_text[:400] if raw_text else "",
            "key_factors": [], "value_assessment": "", "risk_level": "MEDIUM",
            "insight_tags": [], "error": None,
        }
    except Exception as exc:
        logger.error(f"Claude insights error: {exc}")
        return {**_no_key(), "error": str(exc)}
