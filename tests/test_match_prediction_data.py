from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.api.routes import matches
from app.services.odds_api import OddsData
from app.services import sportsdb_api
from app.services import public_football_data


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


@pytest.mark.asyncio
async def test_recent_form_falls_back_to_static_history(monkeypatch):
    class EmptyResult:
        def scalars(self):
            return self

        def all(self):
            return []

    class EmptyDatabase:
        async def execute(self, _statement):
            return EmptyResult()

    kickoff = datetime(2026, 9, 1, tzinfo=timezone.utc)
    history = [
        SimpleNamespace(
            home_team="Arsenal FC",
            away_team="Chelsea FC",
            home_goals=2,
            away_goals=1,
            kickoff_time=kickoff,
        ),
        SimpleNamespace(
            home_team="Liverpool FC",
            away_team="Arsenal FC",
            home_goals=2,
            away_goals=0,
            kickoff_time=kickoff.replace(day=2),
        ),
    ]
    monkeypatch.setattr(matches, "_static_history_for_team", lambda *args, **kwargs: history)

    result = await matches._recent_form(
        EmptyDatabase(),
        "Arsenal FC",
        before=datetime(2026, 10, 1, tzinfo=timezone.utc),
        sport="football",
    )

    assert result["matches_played"] == 2
    assert result["form"] == "LW"
    assert result["matches"][0]["outcome"] == "home"


@pytest.mark.asyncio
async def test_prediction_diagnostics_fills_missing_legacy_recent_form(monkeypatch):
    kickoff = datetime(2026, 10, 1, tzinfo=timezone.utc)
    match = SimpleNamespace(
        id=42,
        external_id="fixture-42",
        source="sportsdb",
        home_team="Arsenal FC",
        away_team="Chelsea FC",
        sport="football",
        kickoff_time=kickoff,
    )
    prediction = SimpleNamespace(
        provenance={},
        status="READY",
        error_message=None,
        home_prob=0.5,
        draw_prob=0.25,
        away_prob=0.25,
    )

    class Result:
        def __init__(self, value):
            self.value = value

        def scalar_one_or_none(self):
            return self.value

    class FakeDatabase:
        def __init__(self):
            self.results = [Result(match), Result(prediction)]

        async def execute(self, _statement):
            return self.results.pop(0)

    async def form_for_team(_db, team, _before, sport=None):
        return {"form": "WDL", "matches_played": 3, "team": team, "sport": sport}

    monkeypatch.setattr(matches, "_recent_form", form_for_team)

    result = await matches.get_prediction_diagnostics(42, FakeDatabase())

    assert result["recent_form"]["home"]["matches_played"] == 3
    assert result["recent_form"]["away"]["team"] == "Chelsea FC"


@pytest.mark.asyncio
async def test_scoped_historical_refresh_skips_global_day_scan(monkeypatch):
    kickoff = datetime(2026, 9, 18, tzinfo=timezone.utc)
    cutoff = datetime(2026, 10, 1, tzinfo=timezone.utc)
    event = {
        "external_id": None,
        "home_team": "Mainz",
        "away_team": "Leverkusen",
        "league": "bundesliga",
        "kickoff_time": kickoff,
        "status": "settled",
        "home_goals": 0,
        "away_goals": 2,
        "actual_outcome": "away",
        "source": "football-data-uk",
    }

    async def get_public_history(before, teams, league):
        assert before == cutoff
        assert teams == {"1. FSV Mainz 05", "Bayer 04 Leverkusen"}
        assert league == "bundesliga"
        return [event]

    async def fail_global_scan(*args, **kwargs):
        raise AssertionError("fixture refresh must not run the global date scan")

    class EmptyResult:
        def scalars(self):
            return self

        def all(self):
            return []

    class FakeDatabase:
        def __init__(self):
            self.added = []

        async def execute(self, _statement):
            return EmptyResult()

        def add(self, row):
            self.added.append(row)

        async def commit(self):
            return None

    monkeypatch.setattr(public_football_data, "fetch_historical_matches", get_public_history)
    monkeypatch.setattr(sportsdb_api, "fetch_historical_range", fail_global_scan)
    db = FakeDatabase()

    result = await sportsdb_api.sync_and_insert_historical(
        db,
        before=cutoff,
        teams={"1. FSV Mainz 05", "Bayer 04 Leverkusen"},
        league="bundesliga",
    )

    assert result["inserted"] == 1
    assert db.added[0].home_goals == 0
    assert db.added[0].away_goals == 2