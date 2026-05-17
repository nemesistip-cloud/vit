"""app/services/deepseek_insights.py — DeepSeek match insights via shared AI cascade."""

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
    from app.services.deterministic_insights import generate_deterministic_insights
    result = generate_deterministic_insights(
        home_team=home_team or "Home", away_team=away_team or "Away",
        league=league or "default", home_prob=home_prob, draw_prob=draw_prob,
        away_prob=away_prob, over_25_prob=over_25_prob, btts_prob=btts_prob,
        bet_side=bet_side, edge=edge, entry_odds=entry_odds, confidence=confidence,
    )
    return {**result, "source": "vit-statistical-engine", "available": True}


def _build_prompt(
    home_team, away_team, league, home_prob, draw_prob, away_prob,
    over_25_prob, btts_prob, bet_side, edge, entry_odds, confidence
) -> str:
    league_label = league.replace("_", " ").title()
    ou   = f"- Over 2.5 Goals: {over_25_prob*100:.1f}%" if over_25_prob is not None else ""
    btts = f"- Both Teams to Score: {btts_prob*100:.1f}%" if btts_prob is not None else ""
    return f"""You are a sharp football betting analyst with deep knowledge of statistical models and market inefficiencies. Provide an independent probability assessment.

Match: {home_team} vs {away_team} | League: {league_label}

VIT ML Ensemble probabilities:
- Home Win: {home_prob*100:.1f}% | Draw: {draw_prob*100:.1f}% | Away Win: {away_prob*100:.1f}%
{ou}
{btts}
Value signal: Side={str(bet_side).upper()}, Edge={edge*100:.2f}%, Odds={f"{entry_odds:.2f}" if entry_odds else "N/A"}, Confidence={confidence*100:.0f}%

Return ONLY valid JSON (no markdown, no code fences):
{{
  "home_prob": 0.00,
  "draw_prob": 0.00,
  "away_prob": 0.00,
  "confidence": 0.00,
  "summary": "2-3 sentence analysis",
  "key_factors": ["factor 1", "factor 2", "factor 3"],
  "value_assessment": "1-2 sentences on betting value",
  "recommendation": "BUY|SELL|HOLD with brief reason",
  "risk_level": "LOW",
  "insight_tags": ["tag1", "tag2"]
}}

Probabilities must sum exactly to 1.0. risk_level must be LOW, MEDIUM, or HIGH."""


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

    try:
        result = await call_ai_with_provider(prompt, max_tokens=600, temperature=0.5, preferred="deepseek")
        if not result:
            return _scie_fallback(
                home_team=home_team, away_team=away_team, league=league,
                home_prob=home_prob, draw_prob=draw_prob, away_prob=away_prob,
                over_25_prob=over_25_prob, btts_prob=btts_prob,
                bet_side=bet_side, edge=edge, entry_odds=entry_odds, confidence=confidence,
            )

        text, provider = result
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        data = json.loads(text)
        total = data.get("home_prob", 0) + data.get("draw_prob", 0) + data.get("away_prob", 0)
        if total > 0:
            data["home_prob"] = round(data["home_prob"] / total, 4)
            data["draw_prob"] = round(data["draw_prob"] / total, 4)
            data["away_prob"] = round(data["away_prob"] / total, 4)

        return {
            "available": True,
            "source": "deepseek",
            "provider": provider,
            "home_prob": data.get("home_prob", home_prob),
            "draw_prob": data.get("draw_prob", draw_prob),
            "away_prob": data.get("away_prob", away_prob),
            "confidence": min(1.0, max(0.0, data.get("confidence", confidence))),
            "summary": data.get("summary", ""),
            "key_factors": data.get("key_factors", []),
            "value_assessment": data.get("value_assessment", ""),
            "recommendation": data.get("recommendation", "HOLD"),
            "risk_level": data.get("risk_level", "MEDIUM"),
            "insight_tags": data.get("insight_tags", []),
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning("[deepseek-insights] parse error: %s", e)
        return _scie_fallback(
            home_team=home_team, away_team=away_team, league=league,
            home_prob=home_prob, draw_prob=draw_prob, away_prob=away_prob,
            over_25_prob=over_25_prob, btts_prob=btts_prob,
            bet_side=bet_side, edge=edge, entry_odds=entry_odds, confidence=confidence,
        )
    except Exception as e:
        logger.error("[deepseek-insights] unexpected error: %s", e)
        return _scie_fallback(
            home_team=home_team, away_team=away_team, league=league,
            home_prob=home_prob, draw_prob=draw_prob, away_prob=away_prob,
        )


async def generate_network_explanation(
    match_data: dict,
    prediction_result: dict,
) -> str:
    """
    Synthesize the 13-model ensemble results into a natural language explanation.
    Used for the 'DeepSeek Analysis' section in the frontend.
    """
    from app.services.ai_client import call_ai_with_provider

    home_team = match_data.get("home_team", "Home")
    away_team = match_data.get("away_team", "Away")
    league = match_data.get("league", "League")

    pred = prediction_result.get("predictions", {})
    home_prob = pred.get("home_prob", 0.33)
    draw_prob = pred.get("draw_prob", 0.33)
    away_prob = pred.get("away_prob", 0.34)

    agreement = pred.get("model_agreement", 0.0)
    top_model = pred.get("top_model", "Statistical Ensemble")
    edge = pred.get("edge", 0.0)

    prompt = f"""You are the VIT Intelligence Network's core analysis agent.
Summarize why our 13-model ML ensemble reached its conclusion for {home_team} vs {away_team} ({league}).

Ensemble Stats:
- Probabilities: Home {home_prob*100:.1f}%, Draw {draw_prob*100:.1f}%, Away {away_prob*100:.1f}%
- Model Agreement: {agreement:.1f}%
- Value Edge: {edge*100:.2f}%
- Top Contributing Model: {top_model}

Write a professional, 3-sentence technical summary explaining the 'why' behind these numbers.
Focus on the convergence of different mathematical signals (Poisson, ELO, Market Implied).
Do not use bullet points or markdown headers. Just plain text.
"""

    try:
        result = await call_ai_with_provider(prompt, max_tokens=150, temperature=0.4, preferred="deepseek")
        if result:
            text, _ = result
            return text.strip()
    except Exception as e:
        logger.warning("Failed to generate network explanation: %s", e)

    # Fallback explanation
    return f"The ensemble reached {agreement:.1f}% agreement on this fixture, led by {top_model}. " \
           f"With a {edge*100:.1f}% edge detected, the statistical consensus favors " \
           f"{'Home' if home_prob > away_prob else 'Away'} based on market-implied liquidity and Poisson goal share."
