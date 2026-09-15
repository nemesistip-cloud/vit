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


def test_fmt_match_fails_closed_for_malformed_prediction_provenance():
    match = SimpleNamespace(
        id=42,
        external_id="sportsdb-event-2487506",
        home_team="Rayo Vallecano",
        away_team="Espanyol",
        league="la_liga",
        sport="football",
        kickoff_time=datetime.now(timezone.utc),
        status="scheduled",
        opening_odds_home=2.1,
        closing_odds_home=None,
        opening_odds_draw=3.2,
        closing_odds_draw=None,
        opening_odds_away=3.7,
        closing_odds_away=None,
        home_goals=None,
        away_goals=None,
        actual_outcome=None,
        source="sportsdb",
        updated_at=None,
    )
    prediction = SimpleNamespace(
        is_seed=False,
        source="live_generated",
        status="READY",
        provenance={"evidence_score": "not-a-number"},
        timestamp=datetime.now(timezone.utc),
        home_prob=0.5,
        draw_prob=0.25,
        away_prob=0.25,
        over_25_prob=None,
        under_25_prob=None,
        btts_prob=None,
        no_btts_prob=None,
        confidence=0.6,
        bet_side="home",
        vig_free_edge=0.1,
        final_ev=None,
        entry_odds=2.1,
    )

    result = matches._fmt_match(match, prediction)

    assert result["prediction_status"] == "failed"
    assert result["evidence"]["score"] == 0.0


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


@pytest.mark.asyncio
async def test_refresh_prediction_odds_includes_live_provider_markets(monkeypatch):
    calls = []

    class FakeOddsClient:
        async def get_odds_for_competition(self, competition, days_ahead, include_live=False):
            calls.append((competition, days_ahead, include_live))
            return [
                OddsData(
                    match_id="odds-api-live-123",
                    home_team="Rayo Vallecano",
                    away_team="Espanyol",
                    home_odds=1.4,
                    draw_odds=4.6,
                    away_odds=8.0,
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
        id=100,
        external_id="564678",
        home_team="Rayo Vallecano de Madrid",
        away_team="RCD Espanyol de Barcelona",
        league="la_liga",
        sport="football",
        status="live",
        kickoff_time=datetime.now(timezone.utc),
    )

    result = await matches._refresh_prediction_odds(match, datetime.now(timezone.utc))

    assert calls and calls[0][0] == "la_liga"
    assert calls[0][2] is True
    assert [item.fixture_id for item in result] == ["odds-api-live-123"] * 3