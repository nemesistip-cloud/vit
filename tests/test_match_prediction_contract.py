"""Regression tests for unavailable match prediction data."""

from types import SimpleNamespace

import pytest

from app.api.routes.matches import _fmt_match
from app.services.prediction_seeder import _make_prediction
import app.services.sportsdb_api as sportsdb_api


def _match(**overrides):
    values = {
        "id": 1,
        "external_id": "external-1",
        "home_team": "Home",
        "away_team": "Away",
        "league": "premier_league",
        "kickoff_time": None,
        "status": "upcoming",
        "source": "test",
        "sport": "football",
        "opening_odds_home": None,
        "opening_odds_draw": None,
        "opening_odds_away": None,
        "closing_odds_home": None,
        "closing_odds_draw": None,
        "closing_odds_away": None,
        "home_goals": None,
        "away_goals": None,
        "actual_outcome": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_missing_prediction_is_not_serialized_as_zero():
    payload = _fmt_match(_match(), pred=None, markets=[{"id": "1x2", "status": "active"}])

    assert payload["home_prob"] is None
    assert payload["draw_prob"] is None
    assert payload["away_prob"] is None
    assert payload["confidence"] is None
    assert payload["over_25_prob"] is None
    assert payload["edge"] is None


def test_odds_do_not_become_prediction_data_without_model_prediction():
    payload = _fmt_match(
        _match(opening_odds_home=2.0, opening_odds_draw=3.5, opening_odds_away=4.0),
        pred=None,
        markets=[{"id": "1x2", "status": "active"}],
    )

    assert payload["home_prob"] is None
    assert payload["draw_prob"] is None
    assert payload["away_prob"] is None
    assert payload["confidence"] is None
    assert payload["odds"] == {"home": 2.0, "draw": 3.5, "away": 4.0}


def test_seed_prediction_does_not_default_every_pick_to_home():
    seen = {"home": 0, "draw": 0, "away": 0}
    for i in range(20):
        match = _match(league="premier_league")
        pred = _make_prediction(match, seed_idx=i)
        assert pred is not None
        seen[pred.bet_side] += 1

    assert seen["home"] > 0
    assert seen["away"] > 0
    assert seen["home"] < 20
    assert seen["away"] < 20


@pytest.mark.asyncio
async def test_fetch_next_events_includes_multi_sport_leagues(monkeypatch):
    seen = set()

    async def fake_fetch(path: str, timeout: int = 15):
        seen.add(path)
        lid = path.split("id=")[-1]
        if lid == "4387":
            return [{
                "idEvent": "nba-1",
                "strHomeTeam": "Lakers",
                "strAwayTeam": "Celtics",
                "strSport": "Basketball",
                "dateEvent": "2026-08-23",
                "strTime": "20:00:00",
                "strStatus": "Scheduled",
                "strLeague": "NBA",
            }]
        if lid == "4908":
            return [{
                "idEvent": "tennis-1",
                "strHomeTeam": "Djokovic",
                "strAwayTeam": "Medvedev",
                "strSport": "Tennis",
                "dateEvent": "2026-08-24",
                "strTime": "11:00:00",
                "strStatus": "Scheduled",
                "strLeague": "Australian Open",
            }]
        return []

    monkeypatch.setattr(sportsdb_api, "_fetch", fake_fetch)

    events = await sportsdb_api.fetch_next_events()

    assert any(ev["sport"] == "basketball" for ev in events)
    assert any(ev["sport"] == "tennis" for ev in events)
    assert any("id=4387" in call for call in seen)
    assert any("id=4908" in call for call in seen)