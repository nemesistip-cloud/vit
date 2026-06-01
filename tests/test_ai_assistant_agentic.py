import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.api.routes.ai_assistant import assistant_status
from app.api.routes.ai_assistant import assistant_chat

@pytest.mark.asyncio
async def test_assistant_chat_native():
    result = await assistant_chat(MagicMock(message="hello"))
    assert result["available"] is True
    assert "powered by native AI" in result["reply"]

@pytest.mark.asyncio
async def test_assistant_status_native():
    result = await assistant_status()
    assert result["available"] is True
    assert result["backend_ai_available"] is True
    assert result["provider"] == "native"
