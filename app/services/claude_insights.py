"""app/services/claude_insights.py — Claude match insights via shared AI cascade.

Uses call_ai() cascade (Gemini→Claude→OpenAI→Grok→Puter) instead of an
isolated httpx client so every insight request benefits from full failover.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _scie_fallback(
    home_team: str = "", away_team: str = "", league: str = "default",
    home_prob: float = 0.45, draw_prob: float = 0.26, away_prob: float = 0.29,
    over_25_prob=None, btts_prob=None, bet_side=None,
    edge: float = 0.0, entry_odds=None, confidence: float = 0.5,
) -> dict:
    """Return a fully-populated deterministic insight when Claude (and all other LLMs) are unavailable."""
    from app.services.deterministic_insights import generate_deterministic_insights
    result = generate_deterministic_insights(
        home_team=home_team or "Home", away_team=away_team or "Away",
        league=league or "default", home_prob=home_prob, draw_prob=draw_prob,
        away_prob=away_prob, over_25_prob=over_25_prob, btts_prob=btts_prob,
        bet_side=bet_side, edge=edge, entry_odds=entry_odds, confidence=confidence,
    )
    return {**result, "source": "vit-statistical-engine", "available": True}


def _no_key() -> dict:
    return _scie_fallback()


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
  "recommendation": "BUY|SELL|HOLD with brief reason",
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
    from app.services.ai_client import call_ai_with_provider

    prompt = _build_prompt(
        home_team, away_team, league, home_prob, draw_prob, away_prob,
        over_25_prob, btts_prob, bet_side, edge, entry_odds, confidence
    )

    result = await call_ai_with_provider(prompt, max_tokens=600, temperature=0.3, preferred="claude")
    if result is None:
        return _scie_fallback(home_team, away_team, league, home_prob, draw_prob, away_prob,
                              over_25_prob, btts_prob, bet_side, edge, entry_odds, confidence)

    raw, provider = result
    try:
        text = raw.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        parsed = json.loads(text)
        hp = float(parsed.get("home_prob", home_prob))
        dp = float(parsed.get("draw_prob", draw_prob))
        ap = float(parsed.get("away_prob", away_prob))
        total = hp + dp + ap
        if total > 0 and abs(total - 1.0) > 0.01:
            hp /= total; dp /= total; ap /= total
        return {
            "available": True, "source": provider,
            "home_prob": round(hp, 4), "draw_prob": round(dp, 4), "away_prob": round(ap, 4),
            "confidence": float(parsed.get("confidence", 0.7)),
            "summary": parsed.get("summary", ""),
            "key_factors": parsed.get("key_factors", []),
            "value_assessment": parsed.get("value_assessment", ""),
            "recommendation": parsed.get("recommendation", ""),
            "risk_level": parsed.get("risk_level", "MEDIUM"),
            "insight_tags": parsed.get("insight_tags", []),
            "error": None,
        }
    except json.JSONDecodeError:
        return {
            "available": True, "source": provider,
            "home_prob": home_prob, "draw_prob": draw_prob, "away_prob": away_prob,
            "confidence": 0.7, "summary": raw[:400],
            "key_factors": [], "value_assessment": "",
            "recommendation": "", "risk_level": "MEDIUM",
            "insight_tags": [], "error": None,
        }
    except Exception as exc:
        logger.error("claude_insights error: %s", exc)
        return _scie_fallback(home_team, away_team, league, home_prob, draw_prob, away_prob,
                              over_25_prob, btts_prob, bet_side, edge, entry_odds, confidence)
