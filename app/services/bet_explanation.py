# app/services/bet_explanation.py
import logging
from typing import Optional
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)

async def generate_bet_explanation(
    home_team: str,
    away_team: str,
    league: str,
    bet_side: str,
    edge: float,
    odds: float,
    probability: float,
    confidence: float
) -> Optional[str]:
    """Generates a natural language explanation for a recommended bet using DeepSeek."""

    prompt = f"""
    Analyze this football betting opportunity and provide a concise, professional explanation for a bettor.

    Match: {home_team} vs {away_team} ({league})
    Recommended Bet: {bet_side}
    Model Probability: {probability:.1%}
    Market Odds: {odds:.2f}
    Expected Value (Edge): {edge:.1%}
    Confidence Score: {confidence:.1%}

    Explain why this is considered a value bet based on the discrepancy between the model's probability and the market odds.
    Keep the explanation under 45 words and focus on the statistical edge.
    """

    try:
        # Use call_ai which handles the cascade
        response = await call_ai(
            prompt=prompt,
            temperature=0.7
        )
        return response.strip()
    except Exception as e:
        logger.error(f"Failed to generate bet explanation: {e}")
        return None
