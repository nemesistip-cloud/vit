import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.api.routes.ai_assistant import _handle_agentic_query

@pytest.mark.asyncio
async def test_accuracy_query_real_data():
    # Mock DB session
    db = AsyncMock()

    # Mock result for ModelMetadata accuracy
    mock_acc_result = MagicMock()
    mock_acc_result.scalar.return_value = 0.85
    db.execute.return_value = mock_acc_result

    # Mock AIPerformanceRepository
    with patch("app.api.routes.ai_assistant.AIPerformanceRepository") as MockRepo:
        repo_instance = MockRepo.return_value
        perf1 = MagicMock(sample_size=100, accuracy=0.8)
        perf2 = MagicMock(sample_size=200, accuracy=0.9)
        repo_instance.get_all = AsyncMock(return_value=[perf1, perf2])

        # Query for accuracy
        result = await _handle_agentic_query("what is your accuracy?", db)

        assert result["available"] is True
        assert "85.0%" in result["reply"] # From ModelMetadata
        assert "86.7%" in result["reply"] # Weighted avg of 0.8*100 + 0.9*200 / 300 = 260/300 = 86.66%
        assert "300" in result["reply"] # Total samples

@pytest.mark.asyncio
async def test_team_search_no_id():
    db = AsyncMock()

    # Mock MatchRepository.search_by_team
    with patch("app.api.routes.ai_assistant.MatchRepository") as MockMatchRepo:
        match_repo = MockMatchRepo.return_value
        mock_match = MagicMock(id=123)
        match_repo.search_by_team = AsyncMock(return_value=[mock_match])

        # Mock TOOL_MAP["get_match_insights"]
        with patch("app.api.routes.ai_assistant.TOOL_MAP") as MockToolMap:
            insights = {
                "match": {
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "league": "Premier League",
                    "kickoff_time": "2025-01-01"
                },
                "predictions": [{
                    "home_prob": 0.6,
                    "draw_prob": 0.2,
                    "away_prob": 0.2,
                    "confidence": 0.8
                }]
            }
            MockToolMap.__getitem__.return_value = AsyncMock(return_value=insights)

            result = await _handle_agentic_query("insight on Arsenal match", db)

            assert result["available"] is True
            assert "Arsenal" in result["reply"]
            assert "60.0%" in result["reply"] # Home prob

@pytest.mark.asyncio
async def test_native_ai_fallback_with_context():
    db = AsyncMock()

    # Mock system health and accuracy queries
    with patch("app.api.routes.ai_assistant._get_system_health_internal") as MockHealth:
        MockHealth.return_value = {"ai_models_ready": 5, "svi": 1.23, "svi_status": "stable"}

        mock_acc_result = MagicMock()
        mock_acc_result.scalar.return_value = 0.77
        db.execute.return_value = mock_acc_result

        with patch("app.api.routes.ai_assistant.call_ai") as MockCallAI:
            MockCallAI.return_value = "Mocked AI Response"

            result = await _handle_agentic_query("hello", db)

            assert result["reply"] == "Mocked AI Response"
            # Verify call_ai was called with context
            args, kwargs = MockCallAI.call_args
            assert "context" in kwargs
            assert kwargs["context"]["accuracy"] == 0.77
            assert kwargs["context"]["health"]["ai_models_ready"] == 5
