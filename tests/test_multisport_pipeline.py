import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from main import app
from app.db.models import Match
from app.services.sportsdb_api import _map_event, TSDB_SPORT_NAMES

@pytest.fixture(autouse=True)
def mock_auth_disabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("API_KEY", "")


def test_sportsdb_payload_normalization():
    # 1. Basketball payload
    bball_payload = {
        "idEvent": "1001",
        "strEvent": "France Basketball Women vs South Korea Basketball Women",
        "strHomeTeam": "France Basketball Women",
        "strAwayTeam": "South Korea Basketball Women",
        "strSport": "Basketball",
        "strLeague": "FIBA Womens World Cup",
        "dateEvent": "2026-09-05",
        "strTime": "12:00:00",
        "strStatus": "NS",
        "intHomeScore": None,
        "intAwayScore": None,
    }
    mapped_bball = _map_event(bball_payload)
    assert mapped_bball is not None
    assert mapped_bball["external_id"] == "1001"
    assert mapped_bball["sport"] == "basketball"
    assert mapped_bball["status"] == "upcoming"
    assert mapped_bball["home_team"] == "France Basketball Women"

    # 2. Cricket payload
    cricket_payload = {
        "idEvent": "1002",
        "strEvent": "Guyana Amazon Warriors vs Jamaica Kingsmen",
        "strHomeTeam": "Guyana Amazon Warriors",
        "strAwayTeam": "Jamaica Kingsmen",
        "strSport": "Cricket",
        "strLeague": "Caribbean Premier League",
        "dateEvent": "2026-09-06",
        "strTime": "23:00:00",
        "strStatus": "NS",
        "intHomeScore": None,
        "intAwayScore": None,
    }
    mapped_cricket = _map_event(cricket_payload)
    assert mapped_cricket is not None
    assert mapped_cricket["external_id"] == "1002"
    assert mapped_cricket["sport"] == "cricket"
    assert mapped_cricket["status"] == "upcoming"

    # 3. Tennis payload
    tennis_payload = {
        "idEvent": "1003",
        "strEvent": "Jannik Sinner vs Carlos Alcaraz",
        "strHomeTeam": "Jannik Sinner",
        "strAwayTeam": "Carlos Alcaraz",
        "strSport": "Tennis",
        "strLeague": "ATP Wimbledon",
        "dateEvent": "2026-07-12",
        "strTime": "14:00:00",
        "strStatus": "NS",
        "intHomeScore": None,
        "intAwayScore": None,
    }
    mapped_tennis = _map_event(tennis_payload)
    assert mapped_tennis is not None
    assert mapped_tennis["external_id"] == "1003"
    assert mapped_tennis["sport"] == "tennis"
    assert mapped_tennis["status"] == "upcoming"


@pytest.mark.asyncio
async def test_api_matches_filtering_for_all_and_specific_sports(db_session: AsyncSession):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Create test matches across sports
    m_bball = Match(
        external_id="test_bb_1",
        home_team="France Women",
        away_team="Korea Women",
        league="FIBA",
        sport="basketball",
        kickoff_time=now,
        status="upcoming",
        source="sportsdb",
    )
    m_cricket = Match(
        external_id="test_cr_1",
        home_team="Guyana Warriors",
        away_team="Jamaica Kingsmen",
        league="CPL",
        sport="cricket",
        kickoff_time=now,
        status="upcoming",
        source="sportsdb",
    )
    m_tennis = Match(
        external_id="test_tn_1",
        home_team="Jannik Sinner",
        away_team="Carlos Alcaraz",
        league="Wimbledon",
        sport="tennis",
        kickoff_time=now,
        status="upcoming",
        source="sportsdb",
    )
    m_football = Match(
        external_id="test_fb_1",
        home_team="Arsenal",
        away_team="Chelsea",
        league="Premier League",
        sport="football",
        kickoff_time=now,
        status="upcoming",
        source="sportsdb",
    )
    db_session.add_all([m_bball, m_cricket, m_tennis, m_football])
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test sport=basketball
        res_bb = await ac.get("/api/matches/upcoming?sport=basketball")
        assert res_bb.status_code == 200
        matches_bb = res_bb.json()
        assert any(m["home_team"] == "France Women" for m in matches_bb)
        assert all(m.get("sport") == "basketball" for m in matches_bb)

        # Test sport=cricket
        res_cr = await ac.get("/api/matches/upcoming?sport=cricket")
        assert res_cr.status_code == 200
        matches_cr = res_cr.json()
        assert any(m["home_team"] == "Guyana Warriors" for m in matches_cr)
        assert all(m.get("sport") == "cricket" for m in matches_cr)

        # Test sport=tennis
        res_tn = await ac.get("/api/matches/upcoming?sport=tennis")
        assert res_tn.status_code == 200
        matches_tn = res_tn.json()
        assert any(m["home_team"] == "Jannik Sinner" for m in matches_tn)
        assert all(m.get("sport") == "tennis" for m in matches_tn)

        # Test sport=all (should return matches across all sports)
        res_all = await ac.get("/api/matches/upcoming?sport=all")
        assert res_all.status_code == 200
        matches_all = res_all.json()
        sports_found = {m.get("sport") for m in matches_all}
        assert "basketball" in sports_found
        assert "cricket" in sports_found
        assert "tennis" in sports_found
        assert "football" in sports_found
