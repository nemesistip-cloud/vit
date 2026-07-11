import pytest
from datetime import datetime
from app.services.multi_ai_dispatcher import run_multi_ai
from app.db.models import Match

@pytest.mark.asyncio
async def test_run_multi_ai_basic(db_session):
    """Test multi-AI dispatcher with native provider."""
    match = Match(
        id=123,
        home_team="Team A",
        away_team="Team B",
        league="League 1",
        kickoff_time=datetime(2025, 1, 1, 12, 0),
        status="scheduled"
    )
    db_session.add(match)
    await db_session.commit()

    result = await run_multi_ai(match_id=123, db=db_session, sources=["native"])

    assert result["match_id"] == 123
    assert "native" in result["results"]
    assert result["results"]["native"]["available"] is True
    assert result["results"]["native"]["home_prob"] == 0.34

@pytest.mark.asyncio
async def test_run_multi_ai_no_sources(db_session):
    """Test dispatcher handles empty sources by defaulting to native."""
    match = Match(
        id=456,
        home_team="Team A",
        away_team="Team B",
        league="League 1",
        kickoff_time=datetime(2025, 1, 1, 12, 0),
        status="scheduled"
    )
    db_session.add(match)
    await db_session.commit()

    result = await run_multi_ai(match_id=456, db=db_session)

    assert result["match_id"] == 456
    assert "native" in result["results"]
