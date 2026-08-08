"""Regression tests for unavailable match prediction data."""

from types import SimpleNamespace

from app.api.routes.matches import _fmt_match


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