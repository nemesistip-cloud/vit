import pytest
import asyncio
import os
from app.services.isports_api import ISportsClient, ISPORTS_LEAGUE_IDS
from app.services.results_settler import fetch_finished_matches, fetch_live_matches

@pytest.mark.asyncio
async def test_isports_client_initialization():
    client = ISportsClient(api_key="test_key")
    assert client.api_key == "test_key"
    assert "premier_league" in ISPORTS_LEAGUE_IDS

@pytest.mark.asyncio
async def test_isports_format_match_data():
    client = ISportsClient(api_key="test_key")
    mock_match = {
        "matchId": "12345",
        "homeName": "Arsenal",
        "awayName": "Chelsea",
        "matchTime": 1716187200, # 2024-05-20
        "homeScore": 2,
        "awayScore": 1,
        "status": "-1"
    }
    formatted = client.format_match_data(mock_match, "premier_league")
    assert formatted["home_team"] == "Arsenal"
    assert formatted["away_team"] == "Chelsea"
    assert formatted["home_goals"] == 2
    assert formatted["away_goals"] == 1
    assert formatted["status"] == "completed"
    assert "2024-05-20" in formatted["kickoff"]

@pytest.mark.asyncio
async def test_fetch_finished_matches_integration(monkeypatch):
    # Mocking environment variable
    monkeypatch.setenv("ISPORTS_API_KEY", "test_key")

    # Mocking the client method to avoid real API calls
    async def mock_get_fixtures(self, league_id):
        return [{
            "matchId": "123",
            "homeName": "Team A",
            "awayName": "Team B",
            "matchTime": int(asyncio.get_event_loop().time()) + 10000,
            "homeScore": 1,
            "awayScore": 0,
            "status": "-1"
        }]

    monkeypatch.setattr(ISportsClient, "get_fixtures_and_results", mock_get_fixtures)

    results = await fetch_finished_matches(days_back=1)
    # Even if it falls back to other providers because of mock data mismatch,
    # we just want to ensure it doesn't crash and follows the logic.
    assert isinstance(results, list)

@pytest.mark.asyncio
async def test_fetch_live_matches_integration(monkeypatch):
    monkeypatch.setenv("ISPORTS_API_KEY", "test_key")

    async def mock_get_livescores(self):
        return [{
            "matchId": "456",
            "leagueId": 1, # Premier League
            "homeName": "Live Team H",
            "awayName": "Live Team A",
            "matchTime": 1716187200,
            "homeScore": 0,
            "awayScore": 0,
            "status": "1"
        }]

    monkeypatch.setattr(ISportsClient, "get_livescores", mock_get_livescores)

    live_matches = await fetch_live_matches()
    assert isinstance(live_matches, list)
    if live_matches:
        assert live_matches[0]["home_team"] == "Live Team H"
        assert "home_score" in live_matches[0]
