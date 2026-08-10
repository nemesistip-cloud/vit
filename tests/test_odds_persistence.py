from types import SimpleNamespace
from datetime import datetime

import pytest

from app.api.routes import sports
from app.db.models import Match
from sqlalchemy import select


@pytest.mark.asyncio
async def test_odds_sync_persists_valid_provider_prices(db_session, monkeypatch):
    match = Match(
        external_id="sports-odds-regression",
        home_team="Home FC",
        away_team="Away FC",
        league="premier_league",
        sport="football",
        kickoff_time=datetime(2026, 8, 11, 15, 0, 0),
        status="upcoming",
        source="sportsdb",
    )
    db_session.add(match)
    await db_session.commit()

    class FakeOddsClient:
        def __init__(self, api_key):
            assert api_key == "configured-test-key"

        async def get_odds_for_competition(self, league):
            assert league == "premier_league"
            return [SimpleNamespace(
                home_team="home fc",
                away_team="away fc",
                home_odds=2.1,
                draw_odds=3.4,
                away_odds=3.2,
                match_id="odds-event-1",
            )]

    monkeypatch.setenv("ODDS_API_KEY", "configured-test-key")
    monkeypatch.setattr(sports, "OddsAPIClient", FakeOddsClient)

    response = await sports.sync_odds_metadata("premier_league", db_session)

    assert response["odds_updated"] == 1
    refreshed = await db_session.scalar(select(Match).where(Match.id == match.id))
    assert refreshed.opening_odds_home == 2.1
    assert refreshed.opening_odds_draw == 3.4
    assert refreshed.opening_odds_away == 3.2
