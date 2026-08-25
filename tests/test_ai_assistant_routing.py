import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from app.modules.ai.gateway import ai_gateway
from app.services.vit_ai_client import vit_ai_client

@pytest.mark.asyncio
async def test_detect_intent_all_scenarios():
    # 1. "Hi"
    assert ai_gateway.detect_intent("Hi", {}) == "conversational"
    # 2. "Hello"
    assert ai_gateway.detect_intent("Hello", {}) == "conversational"
    # 3. "What can you do?"
    assert ai_gateway.detect_intent("What can you do?", {}) == "conversational"
    # 4. General football knowledge
    assert ai_gateway.detect_intent("Who won the 2022 World Cup?", {}) == "conversational"
    # 5. General VIT Network question
    assert ai_gateway.detect_intent("Tell me about VIT Network", {}) == "conversational"

    # 6. Specific match prediction request
    assert ai_gateway.detect_intent("predict match Arsenal vs Chelsea", {}) == "prediction"
    # 7. Match probabilities
    assert ai_gateway.detect_intent("what are the win probabilities for Real Madrid?", {}) == "prediction"
    # 8. Match odds
    assert ai_gateway.detect_intent("what are the odds for Barcelona?", {}) == "prediction"
    # 9. Structured prediction/features payload
    assert ai_gateway.detect_intent("Analyze match", {"features": [0.5, 0.3, 0.2]}) == "prediction"
    # 10. Invalid or incomplete prediction payload with explicit prediction keyword
    assert ai_gateway.detect_intent("predict match with bad features", {"features": "invalid"}) == "prediction"

@pytest.mark.asyncio
async def test_route_chat_conversational_scenarios():
    with patch.object(vit_ai_client, "call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.return_value = "Hello! I am the VIT AI Assistant."

        # 1. "Hi"
        res1 = await ai_gateway.route_chat("Hi")
        assert res1["status"] == "success"
        assert res1["model_id"] == "llm_consensus_v1"

        # 2. "Hello"
        res2 = await ai_gateway.route_chat("Hello")
        assert res2["status"] == "success"
        assert res2["model_id"] == "llm_consensus_v1"

        # 3. "What can you do?"
        res3 = await ai_gateway.route_chat("What can you do?")
        assert res3["status"] == "success"
        assert res3["model_id"] == "llm_consensus_v1"

@pytest.mark.asyncio
async def test_route_chat_prediction_scenarios():
    with patch.object(vit_ai_client, "call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.return_value = "Forecast: Home Win 60%"

        # 6. Specific match prediction
        res = await ai_gateway.route_chat("predict match Arsenal vs Chelsea")
        assert res["status"] == "success"
        assert res["model_id"] == "ensemble_v1"

        # 9. Structured features
        res_feat = await ai_gateway.route_chat("Evaluate match", features=[0.6, 0.2, 0.2])
        assert res_feat["status"] == "success"
        assert res_feat["model_id"] == "ensemble_v1"

@pytest.mark.asyncio
async def test_consecutive_messages_and_context_switching():
    with patch.object(vit_ai_client, "call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.side_effect = lambda prompt, **kwargs: f"Response to: {prompt}"

        # 12. Multiple consecutive conversational messages
        r1 = await ai_gateway.route_chat("Hi")
        r2 = await ai_gateway.route_chat("How are you?")
        assert r1["model_id"] == "llm_consensus_v1"
        assert r2["model_id"] == "llm_consensus_v1"

        # 13. Multiple consecutive prediction requests
        p1 = await ai_gateway.route_chat("predict match Arsenal vs Chelsea")
        p2 = await ai_gateway.route_chat("forecast for Liverpool vs City")
        assert p1["model_id"] == "ensemble_v1"
        assert p2["model_id"] == "ensemble_v1"

        # 14. Switch from conversation to prediction
        c_to_p = await ai_gateway.route_chat("win probability for Barcelona")
        assert c_to_p["model_id"] == "ensemble_v1"

        # 15. Switch from prediction back to conversation
        p_to_c = await ai_gateway.route_chat("Thanks, tell me a joke")
        assert p_to_c["model_id"] == "llm_consensus_v1"

@pytest.mark.asyncio
async def test_vit_ai_client_model_selection_hardening():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Conversational reply"}

    with patch.object(vit_ai_client, "_execute_with_retry", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_resp

        # Conversational query -> default model must be llm_consensus_v1
        reply = await vit_ai_client.call_ai("What can you do?")
        assert reply == "Conversational reply"

        args, kwargs = mock_exec.call_args
        posted_json = kwargs.get("json") or args[2]
        assert posted_json["model_id"] == "llm_consensus_v1"

@pytest.mark.asyncio
async def test_vit_ai_client_failure_handling():
    with patch.object(vit_ai_client, "_execute_with_retry", new_callable=AsyncMock) as mock_exec:
        mock_exec.side_effect = httpx.HTTPStatusError("500 Internal Server Error", request=MagicMock(), response=MagicMock(status_code=500))

        with pytest.raises(httpx.HTTPStatusError):
            await vit_ai_client.call_ai("Test fail")
