import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from app.db.database import AsyncSessionLocal
from app.modules.blockchain.models import ValidatorProfile
from app.db.models import User

# Uses the module-level AsyncSessionLocal — needs a real migrated database.
pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_validator_metrics_route():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/blockchain/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "active_validators" in data
    assert "total_staked" in data
    assert "circulating_supply" in data

@pytest.mark.asyncio
async def test_active_validators_route():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/blockchain/active")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_me_route_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/blockchain/me")
    # Should be 401 since no token provided
    assert response.status_code == 401
