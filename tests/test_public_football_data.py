from datetime import datetime, timezone

from app.services.public_football_data import _row_to_event


def test_public_csv_row_preserves_score_stats_and_provenance():
    event = _row_to_event(
        {
            "Date": "16/08/2025",
            "HomeTeam": "Tottenham",
            "AwayTeam": "Burnley",
            "FTHG": "3",
            "FTAG": "0",
            "HS": "14",
            "AS": "5",
            "HST": "7",
            "AST": "1",
            "HC": "8",
            "AC": "2",
        },
        "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    )

    assert event["home_team"] == "Tottenham Hotspur FC"
    assert event["actual_outcome"] == "home"
    assert event["statistics"]["home_shots_on_target"] == 7
    assert event["source"] == "football-data-uk"
    assert event["source_url"].endswith("2526/E0.csv")


def test_public_provider_date_only_rows_exclude_cutoff_day():
    event = _row_to_event(
        {
            "Date": "19/09/2026",
            "HomeTeam": "Tottenham",
            "AwayTeam": "Aston Villa",
            "FTHG": "1",
            "FTAG": "0",
        },
        "source",
    )
    assert event["kickoff_time"].date().isoformat() == "2026-09-19"