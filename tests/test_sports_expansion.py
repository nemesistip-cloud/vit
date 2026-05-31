import pytest
from httpx import AsyncClient, ASGITransport
from main import app
import os

@pytest.fixture(autouse=True)
def mock_auth_disabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("API_KEY", "")

@pytest.mark.asyncio
async def test_basketball_prediction():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/predict/basketball", json={
            "home_team": "Lakers",
            "away_team": "Celtics",
            "kickoff_time": "2025-12-25T20:00:00Z",
            "league": "NBA",
            "market_odds": {"home": 1.9, "away": 1.9}
        })
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == 0
    assert "nba_v1" in data["model_weights"]

@pytest.mark.asyncio
async def test_tennis_prediction():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/predict/tennis", json={
            "home_team": "Djokovic",
            "away_team": "Alcaraz",
            "kickoff_time": "2025-07-14T14:00:00Z",
            "league": "Wimbledon",
            "market_odds": {"home": 1.7, "away": 2.1}
        })
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == 0
    assert "atp_v1" in data["model_weights"]
