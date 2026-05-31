import json
from pathlib import Path

from scripts import data_audit


def test_audit_ok(tmp_path):
    csv = tmp_path / "sample.csv"
    csv.write_text("home_team,away_team,home_score,away_score,date\nTeamA,TeamB,1,0,2023-01-01\n")
    expected = ["home_team", "away_team", "home_score", "away_score", "date"]
    summary = data_audit.audit_file(csv, expected_columns=expected)
    assert summary["status"] == "ok"
    assert summary["row_count"] == 1
