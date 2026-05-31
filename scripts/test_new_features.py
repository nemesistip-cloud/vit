#!/usr/bin/env python3
"""
Run basic checks for the new data/training scripts without invoking pytest.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

# 1) Run data_audit on a manifest file
cmd1 = [PY, str(ROOT / "scripts" / "data_audit.py"), "--path", str(ROOT / "data" / "sports" / "basketball" / "nba_matches.csv")]
print("Running:", " ".join(cmd1))
res1 = subprocess.run(cmd1)
print("data_audit exit code:", res1.returncode)

# 2) Create a temporary CSV and run train_model
tmp = ROOT / "tests_tmp"
tmp.mkdir(exist_ok=True)
csv = tmp / "sample_bball.csv"
csv.write_text("home_team,away_team,home_score,away_score,home_odds,away_odds,result\nTeamA,TeamB,80,75,1.5,2.5,HOME\nTeamB,TeamC,70,85,2.0,1.8,AWAY\n")
out = tmp / "model.pkl"
cmd2 = [PY, str(ROOT / "scripts" / "train_model.py"), "--sport", "basketball", "--csv", str(csv), "--output", str(out)]
print("Running:", " ".join(cmd2))
res2 = subprocess.run(cmd2)
print("train_model exit code:", res2.returncode)
print("model exists:", out.exists())

sys.exit(0 if res1.returncode == 0 and res2.returncode == 0 and out.exists() else 2)
