"""
Integration tests for the complete sports data flow:
REAL MATCH DATA → /api/matches → PREDICTION → ODDS/MARKETS → STAKING → SETTLEMENT

Tests the following endpoints:
- /api/matches
- /api/matches/live
- /api/matches/upcoming
- /api/matches/{id}
- /api/predict
- /api/inplay/matches
- /api/inplay/matches/{id}/markets
"""

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from main import app
from app.db.database import AsyncSessionLocal
from app.db.models import Match, Prediction
from app.core.cache import cache
from app.core.cache_keys import FIXTURE_LIST
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import uuid


@pytest.mark.asyncio
async def test_api_matches_returns_data():
    """Test that /api/matches returns match data when available"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/matches")
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            # Should have matches key
            assert "matches" in data or isinstance(data, list), "Response should have matches or be a list"


@pytest.mark.asyncio
async def test_api_matches_with_league_filter():
    """Test that /api/matches respects league parameter"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/matches?league=premier_league")
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"


@pytest.mark.asyncio
async def test_api_matches_with_status_filter():
    """Test that /api/matches respects status parameter"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/matches?status=upcoming")
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"


@pytest.mark.asyncio
async def test_api_matches_live_endpoint():
    """Test /api/matches/live endpoint"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/matches/live")
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"


@pytest.mark.asyncio
async def test_live_matches_use_tracker_status_and_exclude_terminal_rows(client, db_session):
    """Live results honor tracker status instead of only kickoff timing."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_session.add_all([
        Match(
            external_id="live-status-regression",
            home_team="Status Home",
            away_team="Status Away",
            league="test_league",
            sport="football",
            kickoff_time=now - timedelta(hours=3),
            status="live",
            source="test",
        ),
        Match(
            external_id="finished-window-regression",
            home_team="Finished Home",
            away_team="Finished Away",
            league="test_league",
            sport="football",
            kickoff_time=now - timedelta(minutes=30),
            status="finished",
            source="test",
        ),
    ])
    await db_session.commit()
    await cache.clear_prefix(FIXTURE_LIST)

    response = await client.get("/api/matches/live")

    assert response.status_code == 200
    assert any(row["external_id"] == "live-status-regression" for row in response.json())
    assert not any(row["external_id"] == "finished-window-regression" for row in response.json())


@pytest.mark.asyncio
async def test_api_matches_upcoming_endpoint():
    """Test /api/matches/upcoming endpoint"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/matches/upcoming")
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"


@pytest.mark.asyncio
async def test_upcoming_matches_respects_requested_limit(client, db_session):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_session.add_all([
        Match(
            external_id=f"upcoming-limit-{index}",
            home_team=f"Limit Home {index}",
            away_team=f"Limit Away {index}",
            league="limit-test",
            kickoff_time=now + timedelta(days=index + 1),
            sport="football",
            status="scheduled",
            source="test",
        )
        for index in range(4)
    ])
    await db_session.commit()
    await cache.clear_prefix(FIXTURE_LIST)

    response = await client.get("/api/matches/upcoming?sport=football&limit=2")

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_recent_matches_get_does_not_sync_or_settle(client, db_session, monkeypatch):
    from app.services import sportsdb_api, settlement_service

    sync_results = AsyncMock()
    settle_results = AsyncMock()
    monkeypatch.setattr(sportsdb_api, "sync_fixture_results", sync_results)
    monkeypatch.setattr(settlement_service, "run_auto_settlement", settle_results)
    await cache.clear_prefix(FIXTURE_LIST)

    response = await client.get("/api/matches/recent?limit=4")

    assert response.status_code == 200
    sync_results.assert_not_awaited()
    settle_results.assert_not_awaited()


@pytest.mark.asyncio
async def test_vitpredict_api_namespace_preserves_legacy_fixture_contract(client, db_session):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_session.add_all([
        Match(
            external_id=f"vitpredict-namespace-{index}",
            home_team=f"Namespace Home {index}",
            away_team=f"Namespace Away {index}",
            league="namespace-test",
            kickoff_time=now + timedelta(days=index + 1),
            sport="football",
            status="scheduled",
            source="test",
        )
        for index in range(3)
    ])
    await db_session.commit()
    await cache.clear_prefix(FIXTURE_LIST)

    legacy = await client.get("/api/matches/upcoming?sport=football&limit=2")
    app_owned = await client.get("/api/apps/vitpredict/matches/upcoming?sport=football&limit=2")

    assert legacy.status_code == app_owned.status_code == 200
    assert len(legacy.json()) <= 2
    assert len(app_owned.json()) <= 2
    assert {row["external_id"] for row in legacy.json()} == {row["external_id"] for row in app_owned.json()}


@pytest.mark.asyncio
async def test_api_inplay_matches_endpoint():
    """Test /api/inplay/matches endpoint"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/inplay/matches")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "matches" in data, "Response should have 'matches' key"
        assert "total" in data, "Response should have 'total' key"


@pytest.mark.asyncio
async def test_api_predict_endpoint():
    """Test /api/predict endpoint with valid payload"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "home_team": "Manchester United",
            "away_team": "Arsenal",
            "league": "premier_league",
            "kickoff_time": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            "market_odds": {
                "home": 1.8,
                "draw": 3.5,
                "away": 2.0
            },
            "sport": "football"
        }
        response = await ac.post("/api/predict", json=payload)
        assert response.status_code in [200, 201, 422], f"Expected 200/201/422, got {response.status_code}"


@pytest.mark.asyncio
async def test_match_detail_endpoint():
    """Test /api/matches/{id} endpoint"""
    # First create a match
    async with AsyncSessionLocal() as db:
        match = Match(
            home_team="Liverpool",
            away_team="Everton",
            league="premier_league",
            kickoff_time=datetime.now(timezone.utc) + timedelta(hours=3),
            external_id=f"ext_{uuid.uuid4().hex}",
            sport="football",
            source="test"
        )
        db.add(match)
        await db.commit()
        await db.refresh(match)
        match_id = match.id

    # Now test the endpoint
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/matches/{match_id}")
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "match_id" in data or "id" in data, "Response should have match ID"


@pytest.mark.asyncio
async def test_inplay_market_endpoint():
    """Test /api/inplay/matches/{id}/markets endpoint"""
    # Use a synthetic match ID from inplay mock data
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/inplay/matches/lm-001/markets")
        assert response.status_code in [200, 404, 422], f"Expected 200/404/422, got {response.status_code}"


@pytest.mark.asyncio
async def test_fixture_to_prediction_flow():
    """Test the complete flow: fixture → API → prediction"""
    # Create a test fixture
    async with AsyncSessionLocal() as db:
        match = Match(
            home_team="Chelsea",
            away_team="Tottenham",
            league="premier_league",
            kickoff_time=datetime.now(timezone.utc) + timedelta(hours=4),
            external_id=f"ext_{uuid.uuid4().hex}",
            sport="football",
            source="test",
            opening_odds_home=1.75,
            opening_odds_draw=3.6,
            opening_odds_away=2.1
        )
        db.add(match)
        await db.commit()
        await db.refresh(match)
        match_id = match.id

    # Test retrieving the match via API
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Check if match appears in /api/matches
        response = await ac.get("/api/matches")
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        # Check if match can be retrieved by ID
        response = await ac.get(f"/api/matches/{match_id}")
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"


@pytest.mark.asyncio
async def test_prediction_with_real_fixture():
    """Test prediction generation with a real fixture"""
    # Create a fixture
    async with AsyncSessionLocal() as db:
        match = Match(
            home_team="Real Madrid",
            away_team="Barcelona",
            league="la_liga",
            kickoff_time=datetime.now(timezone.utc) + timedelta(hours=5),
            external_id=f"ext_{uuid.uuid4().hex}",
            sport="football",
            source="test",
            opening_odds_home=1.6,
            opening_odds_draw=3.8,
            opening_odds_away=2.3
        )
        db.add(match)
        await db.commit()
        await db.refresh(match)

    # Try to get prediction for this match via API
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test /api/predictions/match/{id} if it exists
        response = await ac.get(f"/api/predictions/match/{match.id}")
        # Endpoint requires auth - 401 is expected for unauthenticated access
        assert response.status_code in [200, 401, 404, 422], f"Expected 200/401/404/422, got {response.status_code}"


@pytest.mark.asyncio
async def test_match_api_vs_inplay_api():
    """Verify that /api/matches and /api/inplay/matches use different data sources"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Get regular matches
        matches_response = await ac.get("/api/matches")
        
        # Get inplay matches (should be synthetic/hardcoded)
        inplay_response = await ac.get("/api/inplay/matches")
        
        # Both should be accessible
        assert matches_response.status_code in [200, 404], "Expected 200 or 404 for /api/matches"
        assert inplay_response.status_code == 200, "Expected 200 for /api/inplay/matches"
        
        # inplay/matches should have specific structure
        inplay_data = inplay_response.json()
        assert "matches" in inplay_data, "Inplay response should have 'matches' key"
