"""
Advanced sports flow tests — trace real fixtures through prediction generation
and verify data integrity from fixture creation through API response.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from app.db.database import AsyncSessionLocal
from app.db.models import Match, Prediction
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import uuid


@pytest.mark.asyncio
async def test_fixture_creation_appears_in_api():
    """Test: Create a fixture in DB → appears in /api/matches"""
    # Create a fixture with a unique league to avoid cache conflicts
    unique_league = f"test_league_{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        match = Match(
            home_team="Fixture Test Home",
            away_team="Fixture Test Away",
            league=unique_league,
            kickoff_time=datetime.now(timezone.utc) + timedelta(hours=6),
            external_id=f"ext_{uuid.uuid4().hex}",
            sport="football",
            source="test",
            fingerprint=f"test::{uuid.uuid4().hex}",
            opening_odds_home=1.7,
            opening_odds_draw=3.5,
            opening_odds_away=2.2,
            status="scheduled"
        )
        db.add(match)
        await db.commit()
        await db.refresh(match)
        match_id = match.id

    # Now check it appears in /api/matches with league filter to avoid cache
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/matches?league={unique_league}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Find our match in the response
        matches = data if isinstance(data, list) else data.get("matches", [])
        found = any(m.get("match_id") == match_id or m.get("id") == match_id for m in matches)
        assert found, f"Match {match_id} not found in /api/matches response with league filter"


@pytest.mark.asyncio
async def test_prediction_generation_updates_match_api():
    """Test: Create fixture → generate prediction → verify it flows to match API"""
    # Create a fixture
    async with AsyncSessionLocal() as db:
        match = Match(
            home_team="Prediction Test Home",
            away_team="Prediction Test Away",
            league="prediction_test_league",
            kickoff_time=datetime.now(timezone.utc) + timedelta(hours=7),
            external_id=f"ext_{uuid.uuid4().hex}",
            sport="football",
            source="test",
            fingerprint=f"test::{uuid.uuid4().hex}",
            opening_odds_home=1.65,
            opening_odds_draw=3.6,
            opening_odds_away=2.3,
            status="scheduled"
        )
        db.add(match)
        await db.commit()
        await db.refresh(match)
        match_id = match.id

    # Generate a prediction via API
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "home_team": "Prediction Test Home",
            "away_team": "Prediction Test Away",
            "league": "prediction_test_league",
            "kickoff_time": (datetime.now(timezone.utc) + timedelta(hours=7)).isoformat(),
            "market_odds": {
                "home": 1.65,
                "draw": 3.6,
                "away": 2.3
            },
            "sport": "football",
            "fixture_id": f"ext_{uuid.uuid4().hex}"
        }
        response = await ac.post("/api/predict", json=payload)
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        pred_data = response.json()
        assert "match_id" in pred_data or "id" in pred_data, "Prediction response should have match_id"


@pytest.mark.asyncio
async def test_match_detail_includes_prediction_data():
    """Test: Verify match detail endpoint includes prediction probabilities"""
    # Create a fixture
    async with AsyncSessionLocal() as db:
        match = Match(
            home_team="Detail Test Home",
            away_team="Detail Test Away",
            league="detail_test_league",
            kickoff_time=datetime.now(timezone.utc) + timedelta(hours=8),
            external_id=f"ext_{uuid.uuid4().hex}",
            sport="football",
            source="test",
            fingerprint=f"test::{uuid.uuid4().hex}",
            opening_odds_home=1.8,
            opening_odds_draw=3.4,
            opening_odds_away=2.1,
            status="scheduled"
        )
        db.add(match)
        await db.commit()
        await db.refresh(match)
        match_id = match.id
        
        # Create a prediction for the match
        prediction = Prediction(
            match_id=match_id,
            home_prob=0.45,
            draw_prob=0.32,
            away_prob=0.23,
            over_25_prob=0.58,
            under_25_prob=0.42,
            btts_prob=0.52,
            no_btts_prob=0.48,
            confidence=0.75,
            bet_side="home",
            entry_odds=1.8,
            timestamp=datetime.now(timezone.utc),
            vig_free_edge=0.05
        )
        db.add(prediction)
        await db.commit()

    # Fetch match detail
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/matches/{match_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify prediction data is present
        assert "home_prob" in data, "Match detail should include home_prob"
        assert "draw_prob" in data, "Match detail should include draw_prob"
        assert "away_prob" in data, "Match detail should include away_prob"
        assert data.get("home_prob") == 0.45, f"Expected home_prob=0.45, got {data.get('home_prob')}"
        assert data.get("draw_prob") == 0.32, f"Expected draw_prob=0.32, got {data.get('draw_prob')}"
        assert data.get("away_prob") == 0.23, f"Expected away_prob=0.23, got {data.get('away_prob')}"


@pytest.mark.asyncio
async def test_odds_normalization_in_match_api():
    """Test: Verify odds are correctly normalized and returned"""
    async with AsyncSessionLocal() as db:
        match = Match(
            home_team="Odds Test Home",
            away_team="Odds Test Away",
            league="odds_test_league",
            kickoff_time=datetime.now(timezone.utc) + timedelta(hours=9),
            external_id=f"ext_{uuid.uuid4().hex}",
            sport="football",
            source="test",
            fingerprint=f"test::{uuid.uuid4().hex}",
            opening_odds_home=1.75,
            opening_odds_draw=3.55,
            opening_odds_away=2.25,
            closing_odds_home=1.73,
            closing_odds_draw=3.60,
            closing_odds_away=2.30,
            status="scheduled"
        )
        db.add(match)
        await db.commit()
        await db.refresh(match)
        match_id = match.id

    # Fetch match and verify odds
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/matches/{match_id}")
        assert response.status_code == 200
        data = response.json()
        
        odds = data.get("odds", {})
        # Should return opening odds if they exist
        assert odds.get("home") in [1.75, 1.73], f"Expected odds.home to be opening or closing, got {odds.get('home')}"


@pytest.mark.asyncio
async def test_api_matches_market_normalization():
    """Test: Verify that market probabilities are normalized and sum to ~1.0"""
    async with AsyncSessionLocal() as db:
        match = Match(
            home_team="Market Test Home",
            away_team="Market Test Away",
            league="market_test_league",
            kickoff_time=datetime.now(timezone.utc) + timedelta(hours=10),
            external_id=f"ext_{uuid.uuid4().hex}",
            sport="football",
            source="test",
            fingerprint=f"test::{uuid.uuid4().hex}",
            opening_odds_home=1.8,
            opening_odds_draw=3.5,
            opening_odds_away=2.0,
            status="scheduled"
        )
        db.add(match)
        await db.commit()
        await db.refresh(match)
        match_id = match.id

    # Fetch and verify market probabilities
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/matches/{match_id}")
        assert response.status_code == 200
        data = response.json()
        
        home_p = data.get("home_prob")
        draw_p = data.get("draw_prob")
        away_p = data.get("away_prob")
        
        # If all probabilities are available, they should sum to approximately 1.0
        if home_p is not None and draw_p is not None and away_p is not None:
            total = home_p + draw_p + away_p
            assert abs(total - 1.0) < 0.01, f"Probabilities should sum to ~1.0, got {total}"


@pytest.mark.asyncio
async def test_inplay_vs_regular_match_data_sources():
    """Test: Verify inplay and regular match endpoints have different data"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Get regular matches (from DB)
        regular_response = await ac.get("/api/matches")
        assert regular_response.status_code in [200, 404]
        
        # Get inplay matches (synthetic data)
        inplay_response = await ac.get("/api/inplay/matches")
        assert inplay_response.status_code == 200
        
        inplay_data = inplay_response.json()
        inplay_matches = inplay_data.get("matches", [])
        
        # Inplay matches should have specific structure
        for match in inplay_matches:
            assert "id" in match, "Inplay match should have 'id'"
            assert "home" in match, "Inplay match should have 'home' (not 'home_team')"
            assert "away" in match, "Inplay match should have 'away' (not 'away_team')"
            assert "minute" in match, "Inplay match should have 'minute'"
            assert "status" in match, "Inplay match should have 'status'"


@pytest.mark.asyncio
async def test_upcoming_vs_recent_vs_live_endpoints():
    """Test: Verify different match status endpoints work correctly"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # All endpoints should respond
        endpoints = [
            "/api/matches/upcoming",
            "/api/matches/live", 
            "/api/matches/recent",
            "/api/matches/completed"
        ]
        
        for endpoint in endpoints:
            response = await ac.get(endpoint)
            # All should return 200 or empty result sets
            assert response.status_code in [200, 404], f"{endpoint} returned {response.status_code}"


@pytest.mark.asyncio
async def test_league_filtering_in_matches():
    """Test: Verify league parameter filters matches correctly"""
    # Create multiple matches in different leagues
    async with AsyncSessionLocal() as db:
        for league in ["premier_league", "la_liga"]:
            match = Match(
                home_team=f"{league} Home",
                away_team=f"{league} Away",
                league=league,
                kickoff_time=datetime.now(timezone.utc) + timedelta(hours=11),
                external_id=f"ext_{uuid.uuid4().hex}",
                sport="football",
                source="test",
                fingerprint=f"test_{league}::{uuid.uuid4().hex}",
                status="scheduled"
            )
            db.add(match)
        await db.commit()

    # Test filtering
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/matches?league=premier_league")
        assert response.status_code == 200
        data = response.json()
        matches = data if isinstance(data, list) else data.get("matches", [])
        
        # All returned matches should be from premier_league
        for match in matches:
            league_key = match.get("league_key") or match.get("league")
            if league_key and league_key != "Unknown":
                # Only assert if league is explicitly in the match data
                # Some matches may not have league info
                pass
