#!/usr/bin/env python3
"""
scripts/retrain_cron.py — Simple retrain loop for sports datasets

This script iterates over entries in `data_manifest.json` and invokes
`scripts/train_model.py` for each dataset found. It's intended to be run
via systemd/tmux/cron or CI, not as a daemon in production.
"""

import json
import os
import re
import subprocess
import sys
import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "data_manifest.json"
PY = sys.executable


def load_manifest():
    if not MANIFEST.exists():
        return []
    try:
        with MANIFEST.open(encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)
        return manifest.get("files", []) if isinstance(manifest, dict) else []
    except Exception:
        return []


def is_training_eligible(entry):
    return entry.get("training_eligible", True) is not False


def model_artifact_path(entry):
    dataset_path = Path(entry.get("path", ""))
    artifact_name = dataset_path.stem
    if not re.fullmatch(r"[A-Za-z0-9_-]+", artifact_name):
        raise ValueError("Manifest dataset path must have a safe filename")
    return ROOT / "models" / f"{artifact_name}_baseline.pkl"


def main():
    files = load_manifest()
    # After training runs, attempt to compute and persist rolling-window metrics
    try:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "collect_metrics.py")], check=False, cwd=str(ROOT))
    except Exception:
        print("Warning: metrics collection call failed (continuing)")
    if not files:
        print("No manifest entries found.")
        return 1

    training_files = [entry for entry in files if is_training_eligible(entry)]
    for entry in files:
        if not is_training_eligible(entry):
            print(f"Skipping ineligible dataset: {entry.get('sport', 'unknown')} / {entry.get('name', 'unnamed')}")
    if not training_files:
        print("No training-eligible manifest entries found.")
        return 1

    failures = 0
    for entry in training_files:
        path = entry.get("path")
        sport = entry.get("sport")
        if not path or not sport:
            failures += 1
            print(f"Skipping invalid manifest entry: {entry!r}")
            continue
        csv_path = ROOT / path
        if not csv_path.exists():
            print(f"Skipping missing file: {csv_path}")
            failures += 1
            continue
        try:
            model_path = model_artifact_path(entry)
        except ValueError as exc:
            print(f"Skipping invalid model artifact for {sport} ({path}): {exc}")
            failures += 1
            continue
        cmd = [
            PY,
            str(ROOT / "scripts" / "train_model.py"),
            "--sport",
            sport,
            "--csv",
            str(csv_path),
            "--output",
            str(model_path),
        ]
        print("Running:", " ".join(cmd))
        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            print(f"Training failed for {sport} ({path}) with code {proc.returncode}")
            failures += 1
        else:
            # F21: Push to Storage System if enabled
            if os.getenv("TACHYON_STORAGE_ENABLED") == "true":
                 print(f"Pushing {sport} baseline to Tachyon Swarm...")
                 # Simplified async call inside sync loop
                 from app.services.tachyon_client import tachyon_client
                 try:
                     asyncio.run(tachyon_client.upload_model(str(model_path)))
                 except Exception as te:
                     print(f"Tachyon push failed: {te}")
                     failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
