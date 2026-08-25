import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.modules.ai.gateway import ai_gateway
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
