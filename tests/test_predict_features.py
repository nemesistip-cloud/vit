from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.predict_features import (
    _form_block,
    _merge_match_history,
    _recent_matches_for,
    _team_search_terms,
    build_predict_features,
)


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


def test_merge_match_history_deduplicates_provider_and_static_rows():
    kickoff = datetime(2026, 9, 20, tzinfo=timezone.utc)
    database_row = SimpleNamespace(
        home_team="Newcastle United FC",
        away_team="Everton FC",
        home_goals=2,
        away_goals=1,
        kickoff_time=kickoff,
    )
    static_duplicate = SimpleNamespace(
        home_team="Newcastle United",
        away_team="Everton",
        home_goals=2,
        away_goals=1,
        kickoff_time=kickoff,
    )
    older_row = SimpleNamespace(
        home_team="Newcastle United",
        away_team="Everton",
        home_goals=1,
        away_goals=1,
        kickoff_time=datetime(2026, 9, 13, tzinfo=timezone.utc),
    )

    merged = _merge_match_history([database_row], [static_duplicate, older_row], limit=10)

    assert merged == [database_row, older_row]


def test_predict_features_augment_partial_database_history_from_static(monkeypatch):
    import asyncio
    import app.services.predict_features as predict_features

    now = datetime.now(timezone.utc)

    def make_result(team, count, source):
        return [
            SimpleNamespace(
                home_team=team,
                away_team=f"Opponent {index}",
                home_goals=2,
                away_goals=1,
                kickoff_time=now - timedelta(days=index + 1),
                sport="football",
                source=source,
            )
            for index in range(count)
        ]

    home_db = make_result("Newcastle United FC", 2, "sportsdb")
    away_db = make_result("Everton FC", 2, "sportsdb")
    home_static = make_result("Newcastle United", 5, "football-data-uk")
    away_static = make_result("Everton", 5, "football-data-uk")

    async def recent_matches(_db, team, **_kwargs):
        return home_db if "Newcastle" in team else away_db

    async def h2h_matches(_db, *_args, **_kwargs):
        return []

    def static_team(team, **_kwargs):
        return home_static if "Newcastle" in team else away_static

    monkeypatch.setattr(predict_features, "_recent_matches_for", recent_matches)
    monkeypatch.setattr(predict_features, "_h2h_matches", h2h_matches)
    monkeypatch.setattr(predict_features, "_static_history_for_team", static_team)
    monkeypatch.setattr(predict_features, "_static_history_for_pair", lambda *_args, **_kwargs: [])

    features = asyncio.run(build_predict_features(
        object(),
        "Newcastle United FC",
        "Everton FC",
        league="Premier League",
        before=now,
        sport="football",
    ))

    assert features["home_history_sample_size"] == 5
    assert features["away_history_sample_size"] == 5
    assert features["history_sample_size"] == 5
    assert features["feature_completeness"] >= 0.66
    assert {"sportsdb", "football-data-uk"} <= set(features["evidence_providers"])


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