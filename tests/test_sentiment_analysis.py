import pytest
from unittest.mock import patch, AsyncMock
from app.services.sentiment_analysis import analyze_market_sentiment

@pytest.mark.asyncio
async def test_analyze_market_sentiment_positive():
    with patch("app.services.sentiment_analysis.call_ai", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = '{"sentiment_score": 0.9, "sentiment_label": "POSITIVE", "impact_on_odds": "SHORTENING", "key_takeaways": ["T1", "T2", "T3"], "summary": "Great news"}'
        result = await analyze_market_sentiment(["Star player returns"], "Team A")
        assert result["sentiment_label"] == "POSITIVE"
        assert result["impact_on_odds"] == "SHORTENING"

@pytest.mark.asyncio
async def test_analyze_market_sentiment_negative():
    with patch("app.services.sentiment_analysis.call_ai", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = '{"sentiment_score": 0.2, "sentiment_label": "NEGATIVE", "impact_on_odds": "DRIFTING", "key_takeaways": ["T1", "T2", "T3"], "summary": "Bad news"}'
        result = await analyze_market_sentiment(["Star player injured"], "Team B")
        assert result["sentiment_label"] == "NEGATIVE"
        assert result["impact_on_odds"] == "DRIFTING"
