import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.api.routes.ai_assistant import _handle_agentic_query

@pytest.mark.asyncio
async def test_accuracy_query_uses_verified_evaluation_metrics():
    db = AsyncMock()
    metrics = {
        "sample_size": 300,
        "overall_accuracy": 0.867,
        "mean_brier_score": 0.112,
        "mean_log_loss": 0.279,
        "disclaimer": "Verified outcomes only.",
    }

    with patch(
        "app.services.prediction_evaluation_service.PredictionEvaluationService.get_performance_analytics",
        new_callable=AsyncMock,
        return_value=metrics,
    ) as mock_analytics:
        result = await _handle_agentic_query("what is your accuracy?", db)

    mock_analytics.assert_awaited_once_with(db=db, exclude_demo=True)
    assert result["available"] is True
    assert result["data_status"] == "verified_evaluation"
    assert "86.7%" in result["reply"]
    assert "300" in result["reply"]
    assert "Verified outcomes only." in result["reply"]

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
async def test_native_ai_response_receives_verified_context():
    db = AsyncMock()

    with patch("app.api.routes.ai_assistant._get_system_health_internal") as MockHealth:
        MockHealth.return_value = {"status": "available", "ai_models_callable": 5, "svi": 1.23, "svi_status": "stable"}

        with patch("app.api.routes.ai_assistant.call_ai_with_provider", new_callable=AsyncMock) as MockCallAI:
            MockCallAI.return_value = ("Mocked AI Response", "test-provider")
            result = await _handle_agentic_query("hello", db)

    assert result["available"] is True
    assert result["provider"] == "test-provider"
    assert result["reply"] == "Mocked AI Response"
    context = MockCallAI.await_args.kwargs["context"]
    assert context["accuracy"] is None
    assert context["health"]["ai_models_callable"] == 5
    assert "verified live data" in context["evidence_note"]
