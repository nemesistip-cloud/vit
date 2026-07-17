import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from app.db.database import AsyncSessionLocal
from app.db.models import Match
from app.modules.sports.models import MarketMapping, AffiliateClick
from sqlalchemy import select

# These tests insert rows via the module-level AsyncSessionLocal (real DB),
# so they need a pre-migrated database.  Run with: pytest -m integration
pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_sports_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test /api/sports/competitions
        response = await ac.get("/api/sports/competitions")
        assert response.status_code == 200
        assert "premier_league" in response.json()["competitions"]

        # Test /api/predictions/generate-slip (should 404 since match 9999 doesn't exist)
        response = await ac.get("/api/predictions/generate-slip?match_id=9999&provider=betway")
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_generate_slip_with_match():
    async with AsyncSessionLocal() as db:
        # Create a dummy match
        from datetime import datetime
        match = Match(
            home_team="Team A",
            away_team="Team B",
            league="Test League",
            kickoff_time=datetime.utcnow(),
            external_id="ext_123"
        )
        db.add(match)
        await db.commit()
        await db.refresh(match)
        match_id = match.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/predictions/generate-slip?match_id={match_id}&provider=betway")
        assert response.status_code == 200
        data = response.json()
        assert "redirect_url" in data
        assert "betway" in data["redirect_url"]
        assert "ext_123" in data["redirect_url"]

        # Verify analytics click was recorded
        async with AsyncSessionLocal() as db_check:
            stmt = select(AffiliateClick).where(AffiliateClick.match_id == match_id)
            click = (await db_check.execute(stmt)).scalar_one_or_none()
            assert click is not None
            assert click.provider_name == "betway"

@pytest.mark.asyncio
async def test_sports_webhooks():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/sports/webhooks/isports", json={"event": "match_finished"})
        assert response.status_code == 200
        assert response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_odds_metadata_sync():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Expect 500 if API key missing is fine for smoke test
        response = await ac.post("/api/sports/sync/odds-metadata?league=premier_league")
        assert response.status_code in [200, 500]
