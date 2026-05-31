import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.multi_ai_dispatcher import run_multi_ai

@pytest.mark.asyncio
async def test_run_multi_ai_basic():
    """Test multi-AI dispatcher with mocked match and providers."""
    mock_db = AsyncMock()

    # Mock Match
    mock_match = MagicMock()
    mock_match.home_team = "Arsenal"
    mock_match.away_team = "Luton"
    mock_match.league = "Premier League"
    mock_match.id = 123

    # Mock Match Result
    mock_match_result = MagicMock()
    mock_match_result.scalar_one_or_none.return_value = mock_match

    # Mock Prediction Result
    mock_pred_result = MagicMock()
    mock_pred_result.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [mock_match_result, mock_pred_result]

    with patch("app.services.insight_store.load_match_insights") as mock_load:
        mock_load.return_value = {} # Empty cache

        with patch("app.services.multi_ai_dispatcher._call_provider") as mock_call:
            mock_call.return_value = {
                "available": True,
                "home_prob": 0.7,
                "draw_prob": 0.2,
                "away_prob": 0.1,
                "summary": "Mocked analysis"
            }

            with patch("app.services.ai_ingestion.AIIngestionService.ingest_prediction") as mock_ingest:
                mock_ingest.return_value = True

                result = await run_multi_ai(match_id=123, db=mock_db, sources=["gemini"])

                assert result["match_id"] == 123
                assert "gemini" in result["results"]
                assert result["results"]["gemini"]["home_prob"] == 0.7
                assert mock_ingest.called

@pytest.mark.asyncio
async def test_run_multi_ai_timeout():
    """Test dispatcher handles provider timeouts."""
    mock_db = AsyncMock()

    # Mock Match
    mock_match = MagicMock()
    mock_match.home_team = "Arsenal"
    mock_match.away_team = "Luton"
    mock_match.league = "Premier League"

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_match
    mock_db.execute.return_value = mock_res

    with patch("app.services.insight_store.load_match_insights", return_value={}):
        with patch("asyncio.wait_for", side_effect=Exception("Timeout simulated")):
            result = await run_multi_ai(match_id=123, db=mock_db, sources=["claude"])

            assert "claude" in result["results"]
            assert result["results"]["claude"]["available"] is False
            assert "Timeout simulated" in result["results"]["claude"]["error"]
