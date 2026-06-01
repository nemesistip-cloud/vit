"""
app/services/sentiment_analytics.py

Market Sentiment Analytics Service
==================================
Analyses market sentiment from available data sources (odds movements,
injury news, team form) without requiring external NLP API keys.

Returns a sentiment score and signals that can be used by the
NewsSentinelAgent to enrich match analytics reports.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def analyze_market_sentiment(
    match_id: int,
    home_team: str,
    away_team: str,
    injuries: Optional[List[Dict[str, Any]]] = None,
    odds_movement: Optional[Dict[str, Any]] = None,
    news_snippets: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Analyse market sentiment for a given match.

    Parameters
    ----------
    match_id:       Internal match ID.
    home_team:      Home team name.
    away_team:      Away team name.
    injuries:       List of injury dicts (optional).
    odds_movement:  Dict with opening/current odds (optional).
    news_snippets:  List of raw news strings (optional).

    Returns
    -------
    Dict with keys:
        sentiment_score   float  -1.0 (very negative) to +1.0 (very positive)
        home_sentiment    float  sentiment toward home side
        away_sentiment    float  sentiment toward away side
        signals           list   list of signal description strings
        confidence        float  0.0 – 1.0
    """
    signals: List[str] = []
    home_sentiment = 0.0
    away_sentiment = 0.0

    # ── Injury impact ────────────────────────────────────────────────
    if injuries:
        home_injured = [i for i in injuries if home_team.lower() in str(i.get("team", "")).lower()]
        away_injured = [i for i in injuries if away_team.lower() in str(i.get("team", "")).lower()]

        if len(home_injured) >= 3:
            home_sentiment -= 0.3
            signals.append(f"Home side ({home_team}) has {len(home_injured)} injury absences")
        elif len(home_injured) >= 1:
            home_sentiment -= 0.1
            signals.append(f"Home side has minor injury concerns ({len(home_injured)} player(s))")

        if len(away_injured) >= 3:
            away_sentiment -= 0.3
            signals.append(f"Away side ({away_team}) has {len(away_injured)} injury absences")
        elif len(away_injured) >= 1:
            away_sentiment -= 0.1
            signals.append(f"Away side has minor injury concerns ({len(away_injured)} player(s))")

    # ── Odds movement ────────────────────────────────────────────────
    if odds_movement:
        opening = odds_movement.get("opening", {})
        current = odds_movement.get("current", {})

        open_home = float(opening.get("home", 0) or 0)
        curr_home = float(current.get("home", 0) or 0)

        if open_home > 0 and curr_home > 0:
            drift = (curr_home - open_home) / open_home
            if drift < -0.10:
                home_sentiment += 0.25
                signals.append(f"Home odds shortened significantly ({drift:.1%}) — market backing home")
            elif drift > 0.10:
                home_sentiment -= 0.15
                signals.append(f"Home odds drifted ({drift:.1%}) — market moving against home")

    # ── News snippet keyword analytics ───────────────────────────────
    if news_snippets:
        positive_keywords = ["form", "win streak", "confident", "fit", "return", "strong"]
        negative_keywords = ["crisis", "injury", "suspension", "ban", "doubt", "poor form", "struggle"]

        for snippet in news_snippets:
            lower = snippet.lower()
            home_name_lower = home_team.lower()
            away_name_lower = away_team.lower()

            for kw in positive_keywords:
                if kw in lower:
                    if home_name_lower in lower:
                        home_sentiment += 0.05
                    elif away_name_lower in lower:
                        away_sentiment += 0.05

            for kw in negative_keywords:
                if kw in lower:
                    if home_name_lower in lower:
                        home_sentiment -= 0.05
                        signals.append(f"Negative news signal for {home_team}: '{kw}'")
                    elif away_name_lower in lower:
                        away_sentiment -= 0.05
                        signals.append(f"Negative news signal for {away_team}: '{kw}'")

    # ── Clamp to [-1, 1] ────────────────────────────────────────────
    home_sentiment = max(-1.0, min(1.0, home_sentiment))
    away_sentiment = max(-1.0, min(1.0, away_sentiment))
    overall = (home_sentiment - away_sentiment) / 2.0

    confidence = min(1.0, 0.3 + len(signals) * 0.1)

    if not signals:
        signals.append("No significant sentiment signals detected")

    logger.debug(
        "[sentiment] match=%s home=%.2f away=%.2f overall=%.2f signals=%d",
        match_id, home_sentiment, away_sentiment, overall, len(signals),
    )

    return {
        "sentiment_score": round(overall, 3),
        "home_sentiment": round(home_sentiment, 3),
        "away_sentiment": round(away_sentiment, 3),
        "signals": signals,
        "confidence": round(confidence, 3),
    }
