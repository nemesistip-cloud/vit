from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.api.routes import matches
from app.services.odds_api import OddsData


def test_provider_team_names_match_shortened_bookmaker_names():
    assert matches._provider_team_names_match(
        "Rayo Vallecano de Madrid",
        "Rayo Vallecano",
    )
    assert matches._provider_team_names_match(
        "RCD Espanyol de Barcelona",
        "Espanyol",
    )
    assert not matches._provider_team_names_match("Rayo Vallecano", "Real Madrid")


@pytest.mark.asyncio
async def test_refresh_prediction_odds_matches_provider_event_not_sportsdb_id(monkeypatch):
    class FakeOddsClient:
        async def get_odds_for_competition(self, competition, days_ahead):
            assert competition == "la_liga"
            assert days_ahead >= 1
            return [
                OddsData(
                    match_id="odds-api-event-123",
                    home_team="Rayo Vallecano",
                    away_team="Espanyol",
                    home_odds=2.1,
                    draw_odds=3.2,
                    away_odds=3.7,
                    bookmaker="pinnacle",
                    timestamp=datetime.now(timezone.utc),
                )
            ]

    monkeypatch.setattr(
        matches,
        "get_data_loader",
        lambda: SimpleNamespace(odds_client=FakeOddsClient()),
    )
    match = SimpleNamespace(
        id=42,
        external_id="sportsdb-event-2487506",
        home_team="Rayo Vallecano de Madrid",
        away_team="RCD Espanyol de Barcelona",
        league="la_liga",
        sport="football",
        kickoff_time=datetime.now(timezone.utc),
    )

    result = await matches._refresh_prediction_odds(match, datetime.now(timezone.utc))

    assert [item.fixture_id for item in result] == ["odds-api-event-123"] * 3
    assert [item.selection for item in result] == ["home", "draw", "away"]
    assert [item.odds for item in result] == [2.1, 3.2, 3.7]