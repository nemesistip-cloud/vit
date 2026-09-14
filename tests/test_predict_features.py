from types import SimpleNamespace

from app.services.predict_features import _form_block, _team_search_terms


def test_provider_team_aliases_cover_production_names():
    terms = _team_search_terms("FC Internazionale Milano")

    assert "inter milan" in terms
    assert "inter" in terms


def test_form_block_counts_alias_matched_home_team():
    matches = [
        SimpleNamespace(home_team="Inter Milan", away_team="AC Milan", home_goals=2, away_goals=0),
        SimpleNamespace(home_team="FC Internazionale Milano", away_team="Udinese Calcio", home_goals=1, away_goals=1),
    ]

    form = _form_block("FC Internazionale Milano", matches, window=5)

    assert form["n"] == 2
    assert form["gf_pg"] == 1.5
    assert form["ga_pg"] == 0.5