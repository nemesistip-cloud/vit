import pytest
from unittest.mock import patch, AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_analytics_prompt_generation():
    from app.agents.analytics_reporter_agent import _daily_prompt
    stats = {
        "active_users": 10,
        "total_users": 100,
        "new_subscriptions": 5,
        "predictions": 50,
        "ai_sources_ingested": 200,
        "accuracy_rate": 0.65,
        "settled_predictions_7d": 100,
        "avg_confidence": 0.75,
        "avg_edge": 0.04,
        "pending_withdrawals": 2,
        "upcoming_matches": 15,
        "agent_insights_today": 3
    }
    prompt = _daily_prompt(stats, "2026-05-17", False)
    assert "Daily Intelligence Brief" in prompt
    assert "65.0%" in prompt
    assert "4.00%" in prompt

@pytest.mark.asyncio
async def test_self_healing_diagnosis_parsing():
    from app.agents.self_healing_agent import _diagnose
    snapshot = {"issues": ["test"]}
    with patch("app.services.ai_client.call_ai", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = '{"diagnosis": "ok", "recommendation": "none", "recovery_action": "NONE"}'
        result = await _diagnose(snapshot)
        assert result["recovery_action"] == "NONE"
