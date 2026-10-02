"""Train the Dixon-Coles Platt calibration artifact from real public history.

Run from the repository root with ``PYTHONPATH=backend python scripts/train_odds_free_calibrator.py``.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from app.services.public_football_data import fetch_historical_matches
from services.ml_service.odds_free_model import walk_forward_evaluate


async def main() -> None:
    rows = await fetch_historical_matches()
    report = walk_forward_evaluate(rows)
    gate = report.get("calibration_gate", {})
    artifact = report.get("calibration_artifact")

    def compact(metrics: dict) -> dict:
        return {
            "sample_size": metrics["sample_size"],
            "log_loss": metrics["log_loss"],
            "brier_score": metrics["brier_score"],
            "rps": metrics["rps"],
            "expected_calibration_error": {
                key: value["expected_calibration_error"]
                for key, value in metrics.get("reliability", {}).items()
            },
        }

    summary = {
        "source_matches": len(rows),
        "walk_forward_folds": len(report["folds"]),
        "uncalibrated_out_of_sample": compact(report["out_of_sample"]),
        "calibrated_out_of_sample": compact(report["calibrated_out_of_sample"]),
        "closing_odds_benchmark": compact(report["closing_odds_benchmark"]),
        "paired_log_loss_difference": report["paired_log_loss_difference"],
        "paired_raw_vs_calibrated": report.get("paired_raw_vs_calibrated"),
        "paired_raw_vs_market": report.get("paired_raw_vs_market"),
        "calibration_gate": gate,
        "status": "rejected" if not gate.get("eligible") else "eligible",
    }

    if not gate.get("eligible") or not artifact:
        print(json.dumps(summary, sort_keys=True))
        return

    default_path = Path(__file__).resolve().parents[1] / "models" / "calibrators" / "dixon_coles_walk_forward.json"
    output_path = Path(os.getenv("ODDS_FREE_CALIBRATION_PATH", str(default_path)))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(artifact, sort_keys=True, indent=2), encoding="utf-8")
    temporary_path.replace(output_path)
    summary["calibration_version"] = artifact["calibration_version"]
    summary["calibration_training_matches"] = artifact["training_samples"]
    summary["calibration_training_cutoff"] = artifact["training_cutoff"]
    summary["artifact_path"] = str(output_path)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())