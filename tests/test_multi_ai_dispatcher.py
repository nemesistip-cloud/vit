import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.multi_ai_dispatcher import run_multi_ai

@pytest.mark.asyncio
async def test_run_multi_ai_basic():
    """Test multi-AI dispatcher with native provider."""
    mock_db = AsyncMock()
    result = await run_multi_ai(match_id=123, db=mock_db, sources=["native"])

    assert result["match_id"] == 123
    assert "native" in result["results"]
    assert result["results"]["native"]["available"] is True
    assert result["results"]["native"]["home_prob"] == 0.34

@pytest.mark.asyncio
async def test_run_multi_ai_no_sources():
    """Test dispatcher handles empty sources by defaulting to native."""
    mock_db = AsyncMock()
    result = await run_multi_ai(match_id=456, db=mock_db)

    assert result["match_id"] == 456
    assert "native" in result["results"]
