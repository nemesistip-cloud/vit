from datetime import datetime
from types import SimpleNamespace

from app.services.predict_features import _form_block, _recent_matches_for, _team_search_terms


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


def test_recent_matches_exclude_results_after_prediction_kickoff():
    before = datetime(2026, 9, 19, 11, 30)
    older = SimpleNamespace(
        home_team="Tottenham Hotspur FC",
        away_team="Everton FC",
        home_goals=0,
        away_goals=0,
        kickoff_time=datetime(2026, 9, 12, 16, 30),
    )
    future = SimpleNamespace(
        home_team="Tottenham Hotspur FC",
        away_team="Crystal Palace FC",
        home_goals=2,
        away_goals=1,
        kickoff_time=datetime(2026, 10, 31, 17, 30),
    )

    class FakeResult:
        def scalars(self):
            return self

        def all(self):
            return [older]

    class FakeDb:
        async def execute(self, statement):
            assert "kickoff_time" in str(statement)
            return FakeResult()

    import asyncio
    matches = asyncio.run(_recent_matches_for(FakeDb(), "Tottenham Hotspur FC", before=before))

    assert matches == [older]