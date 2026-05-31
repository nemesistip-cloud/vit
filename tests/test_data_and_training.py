import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def test_data_audit_manifest():
    # Run data_audit on the existing manifest files (should exit 0)
    cmd = [PY, str(ROOT / "scripts" / "data_audit.py"), "--path", str(ROOT / "data" / "sports" / "basketball" / "nba_matches.csv")]
    proc = subprocess.run(cmd)
    assert proc.returncode == 0


def test_train_model_empty_csv_creates_no_model(tmp_path):
    # create a small CSV with one valid row to allow training
    csv = tmp_path / "sample_bball.csv"
    csv.write_text("home_team,away_team,home_score,away_score,home_odds,away_odds,result\nTeamA,TeamB,80,75,1.5,2.5,HOME\n")
    out = tmp_path / "model.pkl"
    cmd = [PY, str(ROOT / "scripts" / "train_model.py"), "--sport", "basketball", "--csv", str(csv), "--output", str(out)]
    proc = subprocess.run(cmd)
    # training should succeed and produce a file
    assert proc.returncode == 0
    assert out.exists()
