"""app/agents/performance_monitor.py

PerformanceMonitorAgent — runs every 30 minutes.

Responsibilities:
  - Compute rolling accuracy / log-loss / Brier for all 12 ensemble models
    using the last 50 settled predictions each (accuracy_enhancer)
  - Detect accuracy drift via AIProfilerService.detect_drift()
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

        metrics: List[Dict] = []
        drift_results: List[Dict] = []
        flagged: List[str] = []

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
                for src in report.get("sources", []):
                    source_name = src.get("source", "")
                    try:
                        drift = await profiler.detect_drift(
                            source_name, window_days=DRIFT_WINDOW_DAYS
                        )
                        drift_results.append({
                            "source":         source_name,
                            "drift_detected": drift.get("drift_detected", False),
                            "magnitude":      drift.get("drift_magnitude", 0.0),
                        })
                        if drift.get("drift_detected") and source_name not in flagged:
                            flagged.append(source_name)
                    except Exception as de:
                        logger.debug("[performance-monitor] drift check failed for %s: %s", source_name, de)
            except Exception as e:
                logger.warning("[performance-monitor] drift detection error: %s", e)

        self.flagged_models = flagged

        result = {
            "model_metrics":  metrics,
            "drift_results":  drift_results,
            "flagged_models": flagged,
            "models_checked": len(metrics),
            "alert_threshold": ACCURACY_ALERT_THRESHOLD,
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
