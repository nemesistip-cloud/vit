"""app/agents/performance_monitor.py

PerformanceMonitorAgent — runs every 30 minutes.

Responsibilities:
  - Compute rolling accuracy / log-loss / Brier for all ensemble models
    using the last 50 settled predictions each (accuracy_enhancer)
  - Detect accuracy drift via AIProfilerService.detect_drift()
  - P2#11: When drift is detected for a source, halve its weight in the live
    orchestrator.model_meta AND in the ModelMetadata DB table.
  - Publish metrics to the AgentCoordinator registry
  - Flag models whose accuracy < ACCURACY_ALERT_THRESHOLD for downstream
    use by the RetrainTriggerAgent
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

ACCURACY_ALERT_THRESHOLD = 0.45   # below this rolling accuracy → flag for review
DRIFT_WINDOW_DAYS        = 30
DRIFT_WEIGHT_HALVE_MIN   = 0.15   # never halve below this floor


class PerformanceMonitorAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="performance-monitor",
            interval_seconds=30 * 60,   # every 30 min
            initial_delay_seconds=90,
        )
        self.flagged_models: List[str] = []

    async def run_cycle(self) -> Dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.services.accuracy_enhancer import rolling_window_accuracy
        from app.services.ai_profiler import AIProfilerService
        from app.core.dependencies import get_orchestrator

        metrics: List[Dict] = []
        drift_results: List[Dict] = []
        flagged: List[str] = []
        drift_reweighted: List[Dict] = []

        async with AsyncSessionLocal() as db:
            # ── 1. Rolling accuracy per model ─────────────────────────
            try:
                rolling = await rolling_window_accuracy(db, window=50)
                for m in rolling:
                    entry = {
                        "model_key":    m.model_key,
                        "samples":      m.samples,
                        "accuracy_1x2": m.accuracy_1x2,
                        "log_loss":     m.log_loss,
                        "brier":        m.brier,
                        "flagged":      m.accuracy_1x2 < ACCURACY_ALERT_THRESHOLD,
                    }
                    metrics.append(entry)
                    if entry["flagged"]:
                        flagged.append(m.model_key)
            except Exception as e:
                logger.warning("[performance-monitor] rolling_window_accuracy error: %s", e)

            # ── 2. Drift detection via AIProfilerService ───────────────
            try:
                profiler = AIProfilerService(db)
                report   = await profiler.get_performance_report()
                orchestrator = get_orchestrator()

                for src in report.get("sources", []):
                    source_name = src.get("source", "")
                    try:
                        drift = await profiler.detect_drift(
                            source_name, window_days=DRIFT_WINDOW_DAYS
                        )
                        drift_detected = drift.get("drift_detected", False)
                        magnitude      = drift.get("drift_magnitude", 0.0)

                        drift_results.append({
                            "source":         source_name,
                            "drift_detected": drift_detected,
                            "magnitude":      magnitude,
                        })

                        if drift_detected and source_name not in flagged:
                            flagged.append(source_name)

                        # ── P2#11: drift → reweight ────────────────────────────
                        if drift_detected and orchestrator is not None:
                            reweight_info = await self._apply_drift_reweight(
                                db, orchestrator, source_name, magnitude
                            )
                            if reweight_info:
                                drift_reweighted.append(reweight_info)

                    except Exception as de:
                        logger.debug("[performance-monitor] drift check failed for %s: %s", source_name, de)
            except Exception as e:
                logger.warning("[performance-monitor] drift detection error: %s", e)

        self.flagged_models = flagged

        result = {
            "model_metrics":    metrics,
            "drift_results":    drift_results,
            "flagged_models":   flagged,
            "drift_reweighted": drift_reweighted,
            "models_checked":   len(metrics),
            "alert_threshold":  ACCURACY_ALERT_THRESHOLD,
        }

        if flagged:
            logger.warning(
                "[performance-monitor] %d model(s) flagged for review: %s",
                len(flagged), flagged,
            )
        else:
            logger.info(
                "[performance-monitor] all %d models within thresholds",
                len(metrics),
            )

        return result

    async def _apply_drift_reweight(
        self,
        db,
        orchestrator,
        source_name: str,
        magnitude: float,
    ) -> Dict | None:
        """
        P2#11: When drift is detected for a model/AI source:
        1. Halve its weight in the live orchestrator.model_meta
        2. Halve its weight in the ModelMetadata DB table
        3. Log the reweighting event

        Only applied when the current weight is above DRIFT_WEIGHT_HALVE_MIN.
        """
        try:
            from sqlalchemy import select
            from app.modules.ai.models import ModelMetadata

            reweighted = False
            old_weight = None
            new_weight = None

            # Halve in live orchestrator
            if source_name in orchestrator.model_meta:
                old_w = orchestrator.model_meta[source_name].get("weight", 1.0)
                if old_w > DRIFT_WEIGHT_HALVE_MIN * 2:
                    new_w = max(DRIFT_WEIGHT_HALVE_MIN, round(old_w * 0.5, 4))
                    orchestrator.model_meta[source_name]["weight"] = new_w
                    old_weight = old_w
                    new_weight = new_w
                    reweighted = True
                    logger.warning(
                        "[performance-monitor] DRIFT reweight: %s weight %.4f → %.4f (magnitude=%.4f)",
                        source_name, old_w, new_w, magnitude,
                    )

            # Halve in DB
            row_res = await db.execute(
                select(ModelMetadata).where(ModelMetadata.key == source_name)
            )
            row = row_res.scalar_one_or_none()
            if row is not None:
                db_old = float(row.weight or 1.0)
                if db_old > DRIFT_WEIGHT_HALVE_MIN * 2:
                    db_new = max(DRIFT_WEIGHT_HALVE_MIN, round(db_old * 0.5, 4))
                    row.weight = db_new
                    await db.commit()
                    reweighted = True

            if reweighted:
                return {
                    "source":     source_name,
                    "old_weight": old_weight,
                    "new_weight": new_weight,
                    "magnitude":  magnitude,
                    "action":     "halved",
                }
        except Exception as exc:
            logger.warning("[performance-monitor] drift reweight failed for %s: %s", source_name, exc)
        return None
