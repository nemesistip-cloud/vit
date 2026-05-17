# app/services/sentiment_analysis.py
import logging
import json
from typing import List, Dict, Any, Optional
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)

async def analyze_market_sentiment(text_snippets: List[str], target_team: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyzes a collection of news headlines or social media posts to determine
    market sentiment and potential odds impact using DeepSeek.
    """

    if not text_snippets:
        return {
            "sentiment_score": 0.5,
            "sentiment_label": "NEUTRAL",
            "impact_on_odds": "STABLE",
            "key_takeaways": []
        }

    combined_text = "\n".join([f"- {s}" for s in text_snippets[:15]])
    target_context = f" specifically for {target_team}" if target_team else ""

    prompt = f"""
    Analyze the following collection of sports news and social media snippets{target_context}:

    {combined_text}

    Tasks:
    1. Determine the overall sentiment score (0.0 = very negative, 1.0 = very positive).
    2. Assess the likely impact on betting market odds (DRIFTING, STABLE, or SHORTENING).
    3. Provide 3 concise key takeaways.

    Return a JSON object with:
    "sentiment_score": float,
    "sentiment_label": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
    "impact_on_odds": "SHORTENING" | "STABLE" | "DRIFTING",
    "key_takeaways": ["...", "...", "..."],
    "summary": "1-sentence summary"
    """

    try:
        response = await call_ai(
            prompt=prompt,
            temperature=0.3
        )
        # Attempt to parse JSON
        clean_json = response.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_json)
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        return {
            "sentiment_score": 0.5,
            "sentiment_label": "NEUTRAL",
            "impact_on_odds": "STABLE",
            "key_takeaways": ["Analysis failed due to system error"],
            "summary": "Unable to determine sentiment at this time."
        }
