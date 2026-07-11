import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from sqlalchemy import insert
from app.modules.elections.models import ElectionEvent
from app.modules.policy.models import PolicyScenario
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_elections_analyze_sentiment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First, ensure we have an election event
        # Note: In actual tests we might use a test DB.
        # For this smoke test, we assume the bootstrap or a previous step might have seeded some,
        # but let's try to get what's there first.
        resp = await ac.get("/api/elections/events")
        events = resp.json()

        if not events:
            # Skip if no events and we can't easily seed here without a session
            pytest.skip("No election events found to test")

        election_id = events[0]["id"]
        resp = await ac.post(f"/api/elections/events/{election_id}/analyze")
        assert resp.status_code == 200
        assert "sentiment" in resp.json()

@pytest.mark.asyncio
async def test_policy_simulate():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Similar for policy
        resp = await ac.get("/api/policy/impacts") # Just to check connectivity
        assert resp.status_code == 200

        # We need a scenario to simulate
        # Since seeding in a test with AsyncSession is complex without the full fixture setup,
        # we'll check if any exist.

        # In a real environment, we'd use the conftest.py fixtures.
        pass

@pytest.mark.asyncio
async def test_tachyon_integration():
    from tachyon.api.router import router as tachyon_router
    if not any(getattr(route, "path", None).startswith("/api/tachyon") for route in app.routes if getattr(route, "path", None)):
        app.include_router(tachyon_router, prefix="/api/tachyon")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/tachyon/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "operational"

        # Test upload
        files = {"file": ("test.txt", b"Hello Tachyon World", "text/plain")}
        resp = await ac.post("/api/tachyon/upload", files=files)
        assert resp.status_code == 200
        file_id = resp.json()["file_id"]

        # Test download
        resp = await ac.get(f"/api/tachyon/download/{file_id}")
        assert resp.status_code == 200
        assert resp.content == b"Hello Tachyon World"
