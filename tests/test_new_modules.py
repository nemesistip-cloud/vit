import pytest
from httpx import AsyncClient, ASGITransport
from main import app
import os

@pytest.fixture(autouse=True)
def mock_auth_disabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("API_KEY", "")

@pytest.mark.asyncio
async def test_elections_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/elections/events")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_policy_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/policy/impacts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_remittance_history_unauthorized(monkeypatch):
    # Enable auth for this specific test
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "test_key")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/remittance/history")
    assert response.status_code == 401
