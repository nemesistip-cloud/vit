import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.api.routes.ai_assistant import assistant_status
from app.api.routes.ai_assistant import assistant_chat

@pytest.mark.asyncio
async def test_assistant_chat_no_key():
    with patch.dict("os.environ", {"NATIVE_AI": "true"}):
        result = await chat("hello")
        assert result["available"] is False
        assert "GEMINI_API_KEY not configured" in result["error"]

@pytest.mark.asyncio
async def test_assistant_chat_with_tools():
    # Mock httpx response to simulate tool calling
    mock_resp_1 = MagicMock()
    mock_resp_1.is_success = True
    mock_resp_1.status_code = 200
    mock_resp_1.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{"functionCall": {"name": "get_upcoming_matches", "args": {"limit": 5}}}]
            }
        }]
    }

    mock_resp_2 = MagicMock()
    mock_resp_2.is_success = True
    mock_resp_2.status_code = 200
    mock_resp_2.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{"text": "I found 5 upcoming matches for you."}]
            }
        }]
    }

    with patch.dict("os.environ", {"NATIVE_AI": "true"}):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_resp_1, mock_resp_2]

            with patch("app.services.assistant_tools.get_upcoming_matches", new_callable=AsyncMock) as mock_get_matches:
                mock_get_matches.return_value = [{"id": 1, "home_team": "A", "away_team": "B"}]

                result = await chat("What are the upcoming matches?")

                assert result["available"] is True
                assert "I found 5 upcoming matches" in result["reply"]
                assert len(result["thoughts"]) == 1
                assert "Executing get_upcoming_matches" in result["thoughts"][0]
                mock_get_matches.assert_called_once_with(limit=5)


@pytest.mark.asyncio
async def test_assistant_status_without_provider_keys():
    with patch.dict("os.environ", {"NATIVE_AI": "true", "NATIVE_AI": "true", "NATIVE_AI": "true"}):
        result = await assistant_status()
        assert result["available"] is False
        assert result["backend_ai_available"] is False
        assert result["configured_providers"] == []
        assert result["provider"] == "puter"
        assert isinstance(result["available_tools"], list)
        assert "get_live_odds" in result["available_tools"]
