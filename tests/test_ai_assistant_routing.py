import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.modules.ai.gateway import ai_gateway
from app.services.ai_client import call_ai
from app.services.vit_ai_client import vit_ai_client

@pytest.mark.asyncio
async def test_detect_intent():
    # Conversational intent
    assert ai_gateway.detect_intent("Hi", {}) == "conversational"
    assert ai_gateway.detect_intent("What can you do?", {}) == "conversational"
    assert ai_gateway.detect_intent("Who won the 2022 World Cup?", {}) == "conversational"

    # Prediction intent via keywords or features
    assert ai_gateway.detect_intent("home_prob 0.5 away_prob 0.3", {}) == "prediction"
    assert ai_gateway.detect_intent("predict match Arsenal vs Chelsea", {"market_odds": {"1": 1.9}}) == "prediction"
    assert ai_gateway.detect_intent("Some prompt", {"features": [1.0, 2.0]}) == "prediction"

@pytest.mark.asyncio
async def test_route_chat_conversational():
    with patch.object(vit_ai_client, "call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.return_value = "Hello! I am the VIT AI Assistant."

        res = await ai_gateway.route_chat("Hi")

        assert res["status"] == "success"
        assert res["provider"] == "vit-ai"
        assert res["model_id"] == "llm_consensus_v1"
        assert res["response"] == "Hello! I am the VIT AI Assistant."
        mock_call_ai.assert_called_once_with("Hi", model="llm_consensus_v1", intent="conversational")

@pytest.mark.asyncio
async def test_route_chat_prediction():
    with patch.object(vit_ai_client, "call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.return_value = "Forecast: Home Win 60%"

        res = await ai_gateway.route_chat("predict match", market_odds={"1": 1.5})

        assert res["status"] == "success"
        assert res["model_id"] == "ensemble_v1"
        mock_call_ai.assert_called_once_with("predict match", model="ensemble_v1", intent="prediction", market_odds={"1": 1.5})

@pytest.mark.asyncio
async def test_vit_ai_client_model_selection():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Conversational reply"}

    with patch.object(vit_ai_client, "_execute_with_retry", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_resp

        # Conversational query -> default model should be llm_consensus_v1
        reply = await vit_ai_client.call_ai("What can you do?")
        assert reply == "Conversational reply"

        # Check posted JSON payload
        args, kwargs = mock_exec.call_args
        posted_json = kwargs.get("json") or args[2]
        assert posted_json["model_id"] == "llm_consensus_v1"

@pytest.mark.asyncio
async def test_vit_ai_client_prediction_features():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Prediction output"}

    with patch.object(vit_ai_client, "_execute_with_retry", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_resp

        # Feature-based query -> default model should be ensemble_v1
        reply = await vit_ai_client.call_ai("Predict", features=[0.1, 0.2])
        assert reply == "Prediction output"

        args, kwargs = mock_exec.call_args
        posted_json = kwargs.get("json") or args[2]
        assert posted_json["model_id"] == "ensemble_v1"


@pytest.mark.asyncio
async def test_vit_ai_client_prediction_always_sends_features():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Prediction output"}

    with patch.object(vit_ai_client, "_execute_with_retry", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_resp

        await vit_ai_client.call_ai("Predict", market_odds={"home": 2.0})

        args, kwargs = mock_exec.call_args
        posted_json = kwargs.get("json") or args[2]
        assert posted_json["model_id"] == "ensemble_v1"
        assert posted_json["payload"]["features"] == {"market_odds": {"home": 2.0}}


@pytest.mark.asyncio
async def test_call_ai_uses_aiml_fallback_when_gateway_fails():
    with patch("app.modules.ai.gateway.ai_gateway.route_chat", new_callable=AsyncMock) as mock_gateway, \
         patch("app.services.ai_client._call_gemini_fallback", new_callable=AsyncMock, return_value=None) as mock_gemini, \
         patch("app.services.ai_client._call_aimlapi_fallback", new_callable=AsyncMock, return_value="AIML live response") as mock_aiml:
        mock_gateway.return_value = {"response": "offline failover", "is_fallback": True}

        response = await call_ai("Launch check")

        assert response == "AIML live response"
        mock_gemini.assert_awaited_once_with("Launch check")
        mock_aiml.assert_awaited_once_with("Launch check")


from app.api.routes.ai_assistant import _handle_agentic_query
from datetime import datetime, timezone
from app.db.models import Match, Prediction

@pytest.mark.asyncio
async def test_agentic_query_highest_confidence_today():
    mock_db = AsyncMock()
    now_utc = datetime.now(timezone.utc)

    mock_match = Match(
        id=1,
        home_team="Arsenal",
        away_team="Chelsea",
        league="Premier League",
        kickoff_time=now_utc.replace(tzinfo=None),
        sport="football",
        status="scheduled"
    )
    mock_pred = Prediction(
        id=10,
        match_id=1,
        home_prob=0.65,
        draw_prob=0.20,
        away_prob=0.15,
        confidence=0.88,
        bet_side="home"
    )

    mock_execute_res = MagicMock()
    mock_execute_res.all.return_value = [(mock_match, mock_pred)]
    mock_db.execute.return_value = mock_execute_res

    res = await _handle_agentic_query("What matches have the highest AI confidence today?", mock_db)
    assert res["available"] is True
    assert "response" in res
    assert "reply" in res
    assert res["response"] == res["reply"]
    assert "Arsenal vs Chelsea" in res["response"]
    assert "88.0%" in res["response"]


@pytest.mark.asyncio
async def test_agentic_query_general_conversational():
    mock_db = AsyncMock()

    mock_scalar_res = MagicMock()
    mock_scalar_res.scalar.return_value = 0.75
    mock_db.execute.return_value = mock_scalar_res

    with patch("app.api.routes.ai_assistant.call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.return_value = "VIT AI is the intelligence network powering forecasts."

        res = await _handle_agentic_query("What is VIT AI?", mock_db)
        assert res["available"] is True
        assert "response" in res
        assert "reply" in res
        assert res["response"] == "VIT AI is the intelligence network powering forecasts."
