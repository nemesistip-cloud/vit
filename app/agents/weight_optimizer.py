"""app/agents/weight_optimizer.py

WeightOptimizerAgent — runs every 6 hours.

Responsibilities:
  - Re-fit the global temperature scaler on all settled predictions
    (TemperatureScaler.fit via fit_temperature_from_history)
  - Update dynamic model weights via ModelAccountability
  - Sync weights across ModelMetadata and ModelPerformance tables
  - Publish a summary of weight deltas to the coordinator registry
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class WeightOptimizerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="weight-optimizer",
            interval_seconds=6 * 3600,   # every 6 hours
            initial_delay_seconds=3 * 60, # start 3 min after boot
        )

    async def run_cycle(self) -> Dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.services.accuracy_enhancer import fit_temperature_from_history
        from app.services.model_accountability import ModelAccountability

        results: Dict[str, Any] = {}

        async with AsyncSessionLocal() as db:
            # ── 1. Temperature calibration ─────────────────────────────
            try:
                temp_result = await fit_temperature_from_history(db, min_samples=50)
                results["temperature_fit"] = temp_result
                if temp_result.get("fitted"):
                    logger.info(
                        "[weight-optimizer] temperature fitted: T=%.4f "
                        "NLL improvement=%.6f (n=%d)",
                        temp_result["temperature"],
                        temp_result["improvement"],
                        temp_result["n_samples"],
                    )
                else:
                    logger.info(
                        "[weight-optimizer] temperature fit skipped: %s",
                        temp_result.get("reason", "unknown"),
                    )
            except Exception as e:
                logger.warning("[weight-optimizer] temperature fit error: %s", e)
                results["temperature_fit"] = {"fitted": False, "error": str(e)}

            # ── 2. Model weight update ─────────────────────────────────
            try:
                ma = ModelAccountability(db)
                await ma.update_model_weights()
                report = await ma.get_model_report()
                results["weight_update"] = {
                    "models_updated": len(report.get("models", [])),
                    "total_weight":   report.get("total_weight", 0.0),
                    "needs_review":   [
                        m["name"] for m in report.get("models", [])
                        if m.get("needs_review")
                    ],
                }
                logger.info(
                    "[weight-optimizer] weights updated: %d models, "
                    "total_weight=%.3f needs_review=%s",
                    results["weight_update"]["models_updated"],
                    results["weight_update"]["total_weight"],
                    results["weight_update"]["needs_review"],
                )
            except Exception as e:
                logger.warning("[weight-optimizer] weight update error: %s", e)
                results["weight_update"] = {"error": str(e)}

            # ── 3. AIProfilerService weight sync ──────────────────────
            try:
                from app.services.ai_profiler import AIProfilerService
                profiler = AIProfilerService(db)
                await profiler.update_weights()
                results["profiler_sync"] = {"synced": True}
            except Exception as e:
                logger.debug("[weight-optimizer] profiler sync error: %s", e)
                results["profiler_sync"] = {"synced": False, "error": str(e)}

        return results
