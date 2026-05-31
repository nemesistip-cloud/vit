import pytest
import httpx

from main import app


@pytest.mark.asyncio
async def test_health_returns_200():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_status_field():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")
    data = response.json()
    assert "status" in data
    assert data["status"] in ("ok", "healthy", "degraded")


@pytest.mark.asyncio
async def test_health_db_connected():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")
    data = response.json()
    assert "db_connected" in data
    assert data["db_connected"] is True


@pytest.mark.asyncio
async def test_health_propagates_request_id():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health", headers={"X-Request-ID": "health-test-123"})
    assert response.headers.get("X-Request-ID") == "health-test-123"
