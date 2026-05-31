"""app/services/grok_advanced.py — Advanced Grok-powered analytics services.

Four capabilities routed through the shared AI cascade (preferred=grok):
  1. social_sentiment_score  — X/social media sentiment for a fixture
  2. news_momentum_predictor — break-even news items affecting odds direction
  3. team_form_narrative     — AI-generated form narrative with recency weighting
  4. breaking_news_scanner   — detect pre-match news that materially affects odds
"""

from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── helpers ────────────────────────────────────────────────────────────────────

def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


async def _call(prompt: str, max_tokens: int = 700, temperature: float = 0.6) -> tuple[Optional[str], str]:
    """Wrapper around the shared AI cascade, preferred=grok. Returns (raw_text, provider)."""
    from app.services.ai_client import call_ai_with_provider
    result = await call_ai_with_provider(prompt, max_tokens=max_tokens, temperature=temperature, preferred="grok")
    if result is None:
        return None, "unavailable"
    return result


# ── 1. Social Sentiment Score ──────────────────────────────────────────────────

async def score_social_sentiment(
    home_team: str,
    away_team: str,
    league: str,
    recent_headlines: Optional[list[str]] = None,
    match_date: Optional[str] = None,
) -> dict:
    """
    Estimate X/social sentiment for a fixture based on team names, league context
    and any recent headlines supplied by the caller.

    Returns: sentiment scores per side, overall market lean, contrarian signal.
    """
    league_label = league.replace("_", " ").title()
    headlines_str = (
        "\n".join(f"- {h}" for h in recent_headlines[:10])
        if recent_headlines else "No headlines provided — use domain knowledge."
    )
    date_str = f"Match date: {match_date}" if match_date else ""

    prompt = f"""You are a social sentiment analyst tracking football-related discourse on X (Twitter), Reddit, and sports forums.

Match: {home_team} vs {away_team} | League: {league_label}
{date_str}

Recent headlines / news snippets:
{headlines_str}

Based on typical social dynamics, historical sentiment patterns, and the headlines above, assess the social media sentiment and return ONLY valid JSON:
{{
  "home_sentiment_score": 0.65,
  "away_sentiment_score": 0.35,
  "overall_market_lean": "home|draw|away|neutral",
  "public_confidence_home": 0.62,
  "public_confidence_away": 0.38,
  "contrarian_signal": true,
  "contrarian_side": "away",
  "sentiment_momentum": "RISING_HOME|RISING_AWAY|STABLE|MIXED",
  "social_volume_estimate": "LOW|MEDIUM|HIGH|VERY_HIGH",
  "key_talking_points": ["point 1", "point 2", "point 3"],
  "fade_public_recommendation": false,
  "narrative": "2-3 sentence sentiment summary",
  "data_quality": "SYNTHETIC|LOW|MEDIUM|HIGH"
}}
Note: If you lack real-time data mark data_quality as SYNTHETIC and use domain knowledge."""

    raw, provider = await _call(prompt, max_tokens=600)
    if raw is None:
        return {"available": False, "error": "AI provider unavailable", "source": "grok"}

    try:
        parsed = json.loads(_strip_fence(raw))
        return {
            "available": True,
            "source": provider,
            "home_sentiment_score": float(parsed.get("home_sentiment_score", 0.5)),
            "away_sentiment_score": float(parsed.get("away_sentiment_score", 0.5)),
            "overall_market_lean": parsed.get("overall_market_lean", "neutral"),
            "public_confidence_home": float(parsed.get("public_confidence_home", 0.5)),
            "public_confidence_away": float(parsed.get("public_confidence_away", 0.5)),
            "contrarian_signal": bool(parsed.get("contrarian_signal", False)),
            "contrarian_side": parsed.get("contrarian_side"),
            "sentiment_momentum": parsed.get("sentiment_momentum", "STABLE"),
            "social_volume_estimate": parsed.get("social_volume_estimate", "MEDIUM"),
            "key_talking_points": parsed.get("key_talking_points", []),
            "fade_public_recommendation": bool(parsed.get("fade_public_recommendation", False)),
            "narrative": parsed.get("narrative", ""),
            "data_quality": parsed.get("data_quality", "SYNTHETIC"),
        }
    except Exception as exc:
        logger.error("social_sentiment parse error: %s", exc)
        return {"available": False, "error": str(exc), "source": provider}


# ── 2. News Momentum Predictor ─────────────────────────────────────────────────

async def predict_news_momentum(
    home_team: str,
    away_team: str,
    league: str,
    news_items: list[dict],
    current_odds: dict,
) -> dict:
    """
    Predict odds direction based on recent news items.

    news_items: [{headline, source, published_at, sentiment_hint}]
    current_odds: {"home": 2.10, "draw": 3.40, "away": 3.60}

    Returns: predicted movement per side, magnitude, confidence, trading signal.
    """
    league_label = league.replace("_", " ").title()
    news_str = json.dumps(news_items[:8], default=str)
    odds_str = f"Home: {current_odds.get('home', 'N/A')} | Draw: {current_odds.get('draw', 'N/A')} | Away: {current_odds.get('away', 'N/A')}"

    prompt = f"""You are a football odds movement analyst with expertise in news-driven market shifts.

Match: {home_team} vs {away_team} | League: {league_label}
Current odds: {odds_str}

Recent news items: {news_str}

Predict how these news items will move the odds market and return ONLY valid JSON:
{{
  "home_odds_direction": "SHORTEN|DRIFT|STABLE",
  "away_odds_direction": "SHORTEN|DRIFT|STABLE",
  "draw_odds_direction": "SHORTEN|DRIFT|STABLE",
  "home_magnitude_pct": 2.5,
  "away_magnitude_pct": 1.2,
  "predicted_home_odds": 2.05,
  "predicted_draw_odds": 3.50,
  "predicted_away_odds": 3.80,
  "most_impactful_news_index": 0,
  "trading_signal": "BUY_HOME|BUY_AWAY|BUY_DRAW|SELL_HOME|SELL_AWAY|LAY_DRAW|HOLD",
  "signal_confidence": 0.70,
  "time_sensitivity": "IMMEDIATE|HOURS|DAYS",
  "narrative": "2-3 sentence explanation of the predicted market movement",
  "risk_warning": "any caveats"
}}"""

    raw, provider = await _call(prompt, max_tokens=600, temperature=0.5)
    if raw is None:
        return {"available": False, "error": "AI provider unavailable", "source": "grok"}

    try:
        parsed = json.loads(_strip_fence(raw))
        return {
            "available": True,
            "source": provider,
            "home_odds_direction": parsed.get("home_odds_direction", "STABLE"),
            "away_odds_direction": parsed.get("away_odds_direction", "STABLE"),
            "draw_odds_direction": parsed.get("draw_odds_direction", "STABLE"),
            "home_magnitude_pct": float(parsed.get("home_magnitude_pct", 0)),
            "away_magnitude_pct": float(parsed.get("away_magnitude_pct", 0)),
            "predicted_home_odds": float(parsed.get("predicted_home_odds", current_odds.get("home", 2.0))),
            "predicted_draw_odds": float(parsed.get("predicted_draw_odds", current_odds.get("draw", 3.3))),
            "predicted_away_odds": float(parsed.get("predicted_away_odds", current_odds.get("away", 3.5))),
            "most_impactful_news_index": int(parsed.get("most_impactful_news_index", 0)),
            "trading_signal": parsed.get("trading_signal", "HOLD"),
            "signal_confidence": float(parsed.get("signal_confidence", 0.5)),
            "time_sensitivity": parsed.get("time_sensitivity", "HOURS"),
            "narrative": parsed.get("narrative", ""),
            "risk_warning": parsed.get("risk_warning", ""),
        }
    except Exception as exc:
        logger.error("news_momentum parse error: %s", exc)
        return {"available": False, "error": str(exc), "source": provider}


# ── 3. Team Form Narrative ─────────────────────────────────────────────────────

async def generate_form_narrative(
    team: str,
    league: str,
    recent_results: list[dict],
    opponent: Optional[str] = None,
) -> dict:
    """
    Generate an AI narrative assessing a team's current form with recency weighting.

    recent_results: [{opponent, result (W/D/L), goals_for, goals_against, was_home}]
    Returns: form rating, trajectory, strengths, weaknesses, narrative.
    """
    league_label = league.replace("_", " ").title()
    opp_str = f" (upcoming opponent: {opponent})" if opponent else ""
    results_str = json.dumps(recent_results[:8], default=str)

    prompt = f"""You are a football form analyst for {team} in {league_label}{opp_str}.

Recent results (most recent first): {results_str}

Analyse the team's form with recency weighting (recent matches carry more weight) and return ONLY valid JSON:
{{
  "form_rating": 7.2,
  "form_string": "WDWLW",
  "trajectory": "RISING|STABLE|DECLINING|VOLATILE",
  "momentum_score": 0.68,
  "goals_scored_avg": 1.6,
  "goals_conceded_avg": 0.8,
  "clean_sheet_rate": 0.4,
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "tactical_style": "Possession|Counter|Direct|High-Press|Defensive",
  "home_away_note": "note on home vs away form if relevant",
  "vs_opponent_note": "head-to-head note if opponent provided",
  "form_narrative": "3-4 sentence form summary with tactical context",
  "betting_implication": "1-2 sentence betting angle"
}}
form_rating is out of 10. momentum_score is 0–1."""

    raw, provider = await _call(prompt, max_tokens=600, temperature=0.6)
    if raw is None:
        return {"available": False, "error": "AI provider unavailable", "source": "grok"}

    try:
        parsed = json.loads(_strip_fence(raw))
        return {
            "available": True,
            "source": provider,
            "team": team,
            "form_rating": float(parsed.get("form_rating", 5.0)),
            "form_string": parsed.get("form_string", ""),
            "trajectory": parsed.get("trajectory", "STABLE"),
            "momentum_score": float(parsed.get("momentum_score", 0.5)),
            "goals_scored_avg": float(parsed.get("goals_scored_avg", 0)),
            "goals_conceded_avg": float(parsed.get("goals_conceded_avg", 0)),
            "clean_sheet_rate": float(parsed.get("clean_sheet_rate", 0)),
            "strengths": parsed.get("strengths", []),
            "weaknesses": parsed.get("weaknesses", []),
            "tactical_style": parsed.get("tactical_style", ""),
            "home_away_note": parsed.get("home_away_note", ""),
            "vs_opponent_note": parsed.get("vs_opponent_note", ""),
            "form_narrative": parsed.get("form_narrative", ""),
            "betting_implication": parsed.get("betting_implication", ""),
        }
    except Exception as exc:
        logger.error("form_narrative parse error: %s", exc)
        return {"available": False, "error": str(exc), "source": provider}


# ── 4. Breaking News Scanner ───────────────────────────────────────────────────

async def scan_breaking_news(
    home_team: str,
    away_team: str,
    league: str,
    hours_before_kickoff: float,
    news_feed: list[dict],
) -> dict:
    """
    Scan a pre-match news feed for material events that should alter predictions.

    news_feed: [{headline, source, published_at, body_snippet}]
    Returns: alert level, triggered events, recommended prediction adjustment.
    """
    league_label = league.replace("_", " ").title()
    news_str = json.dumps(news_feed[:12], default=str)

    prompt = f"""You are a pre-match intelligence scanner for professional football bettors.

Match: {home_team} vs {away_team} | League: {league_label}
Hours until kickoff: {hours_before_kickoff:.1f}

News feed: {news_str}

Scan for material events (manager sacked, key player ruled out, pitch condition, weather, etc.) and return ONLY valid JSON:
{{
  "alert_level": "NONE|LOW|MEDIUM|HIGH|CRITICAL",
  "material_events": [
    {{
      "event_type": "INJURY|SUSPENSION|MANAGER_CHANGE|WEATHER|PITCH|LINEUP|TRANSFER|OTHER",
      "affected_team": "home|away|both",
      "headline": "brief headline",
      "impact": "brief impact description",
      "odds_implication": "SHORTEN_HOME|SHORTEN_AWAY|WIDEN_DRAW|UNKNOWN"
    }}
  ],
  "prediction_adjustment_needed": true,
  "recommended_action": "HOLD|REASSESS|VOID_BET|INCREASE_STAKE|REDUCE_STAKE",
  "confidence_impact": -0.08,
  "summary": "2-3 sentence scanner summary",
  "data_quality": "SYNTHETIC|LIVE"
}}
Mark data_quality SYNTHETIC if you lack real-time news access."""

    raw, provider = await _call(prompt, max_tokens=600, temperature=0.5)
    if raw is None:
        return {"available": False, "error": "AI provider unavailable", "source": "grok"}

    try:
        parsed = json.loads(_strip_fence(raw))
        return {
            "available": True,
            "source": provider,
            "alert_level": parsed.get("alert_level", "NONE"),
            "material_events": parsed.get("material_events", []),
            "prediction_adjustment_needed": bool(parsed.get("prediction_adjustment_needed", False)),
            "recommended_action": parsed.get("recommended_action", "HOLD"),
            "confidence_impact": float(parsed.get("confidence_impact", 0)),
            "summary": parsed.get("summary", ""),
            "data_quality": parsed.get("data_quality", "SYNTHETIC"),
        }
    except Exception as exc:
        logger.error("breaking_news_scanner parse error: %s", exc)
        return {"available": False, "error": str(exc), "source": provider}
