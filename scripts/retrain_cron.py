#!/usr/bin/env python3
"""
scripts/retrain_cron.py — Simple retrain loop for sports datasets

This script iterates over entries in `data_manifest.json` and invokes
`scripts/train_model.py` for each dataset found. It's intended to be run
via systemd/tmux/cron or CI, not as a daemon in production.
"""

import json
import os
import subprocess
import sys
import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data_manifest.json"
PY = sys.executable


def load_manifest():
    if not MANIFEST.exists():
        return []
    try:
        return json.load(MANIFEST).get("files", [])
    except Exception:
        return []


def main():
    # Keep local copy up-to-date with remote before running training jobs
    try:
        subprocess.run(["git", "pull", "origin", "main"], check=True, cwd=str(ROOT))
    except Exception as _e:
        print("Warning: git pull failed — continuing anyway:", _e)
    files = load_manifest()
    # After training runs, attempt to compute and persist rolling-window metrics
    try:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "collect_metrics.py")], check=False, cwd=str(ROOT))
    except Exception:
        print("Warning: metrics collection call failed (continuing)")
    if not files:
        print("No manifest entries found.")
        return 1

    for entry in files:
        path = entry.get("path")
        sport = entry.get("sport")
        if not path or not sport:
            continue
        csv_path = ROOT / path
        if not csv_path.exists():
            print(f"Skipping missing file: {csv_path}")
            continue
        cmd = [PY, str(ROOT / "scripts" / "train_model.py"), "--sport", sport, "--csv", str(csv_path)]
        print("Running:", " ".join(cmd))
        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            print(f"Training failed for {sport} ({path}) with code {proc.returncode}")
        else:
            # F21: Push to Tachyon Fabric if enabled
            if os.getenv("TACHYON_STORAGE_ENABLED") == "true":
                 model_path = ROOT / "models" / f"{sport}_baseline.pkl"
                 print(f"Pushing {sport} baseline to Tachyon Swarm...")
                 # Simplified async call inside sync loop
                 from app.services.tachyon_client import tachyon_client
                 try:
                     asyncio.run(tachyon_client.upload_model(str(model_path)))
                 except Exception as te:
                     print(f"Tachyon push failed: {te}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
