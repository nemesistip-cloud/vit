"""app/agents/performance_monitor.py — Performance Monitor Agent v2

Runs every 30 minutes.

v2 upgrades:
  - Accuracy velocity tracking: computes per-model delta from previous cycle
  - Early-warning system: flags models whose accuracy drops ≥3% in one cycle
  - Brier trend: "up" / "stable" / "down" per model
  - accuracy_velocity dict published in result (consumed by SelfHealingAgent)

Responsibilities:
  - Compute rolling accuracy / log-loss / Brier for all ensemble models
    using the last 50 settled predictions each (accuracy_enhancer)
  - Detect accuracy drift via AIProfilerService.detect_drift()
  - P2#11: When drift is detected for a source, halve its weight in the live
    orchestrator.model_meta AND in the ModelMetadata DB table.
  - Publish metrics to the SwarmOrchestrator result registry
  - Flag models whose accuracy < ACCURACY_ALERT_THRESHOLD for downstream
    use by the RetrainTriggerAgent and SelfHealingAgent
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

ACCURACY_ALERT_THRESHOLD  = 0.45   # below this rolling accuracy → flag for review
ACCURACY_VELOCITY_WARNING = 0.03   # drop of ≥3% in one cycle triggers early warning
BRIER_TREND_DELTA         = 0.01   # delta magnitude to call a trend "up" or "down"
DRIFT_WINDOW_DAYS         = 30
DRIFT_WEIGHT_HALVE_MIN    = 0.15   # never halve below this floor


class PerformanceMonitorAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="performance-monitor",
            interval_seconds=30 * 60,   # every 30 min
            initial_delay_seconds=90,
        )
        self.flagged_models: List[str] = []
        # Previous cycle snapshot for velocity computation
        self._prev_accuracy:  Dict[str, float] = {}
        self._prev_brier:     Dict[str, float] = {}

    async def run_cycle(self) -> Dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.services.accuracy_enhancer import rolling_window_accuracy
        from app.services.ai_profiler import AIProfilerService
        from app.core.dependencies import get_orchestrator

        metrics:          List[Dict]  = []
        drift_results:    List[Dict]  = []
        flagged:          List[str]   = []
        drift_reweighted: List[Dict]  = []
        early_warnings:   List[str]   = []
        accuracy_velocity: Dict[str, float] = {}
        brier_trend:       Dict[str, str]   = {}

        async with AsyncSessionLocal() as db:
            # ── 1. Rolling accuracy per model ──────────────────────────────
            try:
                rolling = await rolling_window_accuracy(db, window=50)
                if len(rolling) < 5:
                    logger.info(
                        "[performance-monitor] bootstrap: only %d model metric rows — "
                        "DB needs more settled predictions. Skipping drift detection.",
                        len(rolling),
                    )
                for m in rolling:
                    acc = m.accuracy_1x2
                    brier = m.brier

                    # Velocity: delta vs previous cycle
                    prev_acc   = self._prev_accuracy.get(m.model_key)
                    prev_brier = self._prev_brier.get(m.model_key)
                    vel   = round(acc - prev_acc, 4) if prev_acc is not None else 0.0
                    b_vel = round(brier - prev_brier, 4) if prev_brier is not None else 0.0

                    accuracy_velocity[m.model_key] = vel

                    # Brier trend (lower is better, so positive delta = worse)
                    if b_vel > BRIER_TREND_DELTA:
                        brier_trend[m.model_key] = "worsening"
                    elif b_vel < -BRIER_TREND_DELTA:
                        brier_trend[m.model_key] = "improving"
                    else:
                        brier_trend[m.model_key] = "stable"

                    # Early warning: accuracy dropped ≥ velocity threshold in 1 cycle
                    is_early_warning = (
                        prev_acc is not None
                        and vel <= -ACCURACY_VELOCITY_WARNING
                    )
                    if is_early_warning:
                        early_warnings.append(
                            f"{m.model_key}: accuracy ↓{abs(vel)*100:.1f}% in one cycle"
                        )
                        logger.warning(
                            "[performance-monitor] EARLY WARNING: %s accuracy dropped %.2f%% "
                            "this cycle (now %.3f)",
                            m.model_key, abs(vel) * 100, acc,
                        )

                    entry = {
                        "model_key":        m.model_key,
                        "samples":          m.samples,
                        "accuracy_1x2":     acc,
                        "log_loss":         m.log_loss,
                        "brier":            brier,
                        "accuracy_velocity": vel,
                        "brier_trend":      brier_trend.get(m.model_key, "stable"),
                        "flagged":          acc < ACCURACY_ALERT_THRESHOLD,
                        "early_warning":    is_early_warning,
                    }
                    metrics.append(entry)
                    if entry["flagged"]:
                        flagged.append(m.model_key)

                # Update previous-cycle snapshots
                self._prev_accuracy = {m.model_key: m.accuracy_1x2 for m in rolling}
                self._prev_brier    = {m.model_key: m.brier         for m in rolling}

            except Exception as e:
                logger.warning("[performance-monitor] rolling_window_accuracy error: %s", e)

            # ── 2. Drift detection via AIProfilerService ───────────────────
            if len(metrics) < 5:
                self.flagged_models = flagged
                return {
                    "model_metrics":     metrics,
                    "drift_results":     drift_results,
                    "flagged_models":    flagged,
                    "drift_reweighted":  drift_reweighted,
                    "models_checked":    len(metrics),
                    "alert_threshold":   ACCURACY_ALERT_THRESHOLD,
                    "accuracy_velocity": accuracy_velocity,
                    "brier_trend":       brier_trend,
                    "early_warnings":    early_warnings,
                    "bootstrap_mode":    True,
                }
            try:
                profiler     = AIProfilerService(db)
                report       = await profiler.get_performance_report()
                orchestrator = get_orchestrator()

                for src in report.get("sources", []):
                    source_name = src.get("source", "")
                    try:
                        drift          = await profiler.detect_drift(source_name, window_days=DRIFT_WINDOW_DAYS)
                        drift_detected = drift.get("drift_detected", False)
                        magnitude      = drift.get("drift_magnitude", 0.0)

                        drift_results.append({
                            "source":         source_name,
                            "drift_detected": drift_detected,
                            "magnitude":      magnitude,
                        })

                        if drift_detected and source_name not in flagged:
                            flagged.append(source_name)

                        if drift_detected and orchestrator is not None:
                            reweight_info = await self._apply_drift_reweight(
                                db, orchestrator, source_name, magnitude
                            )
                            if reweight_info:
                                drift_reweighted.append(reweight_info)

                    except Exception as de:
                        logger.debug(
                            "[performance-monitor] drift check failed for %s: %s",
                            source_name, de,
                        )
            except Exception as e:
                logger.warning("[performance-monitor] drift detection error: %s", e)

        self.flagged_models = flagged

        # Emit swarm event if early warnings found
        if early_warnings:
            try:
                from app.core.swarm_orchestrator import get_swarm
                await get_swarm().emit_event(
                    "accuracy_early_warning", self.name,
                    {"warnings": early_warnings, "models": list(accuracy_velocity.keys())},
                )
            except Exception:
                pass

        result = {
            "model_metrics":     metrics,
            "drift_results":     drift_results,
            "flagged_models":    flagged,
            "drift_reweighted":  drift_reweighted,
            "models_checked":    len(metrics),
            "alert_threshold":   ACCURACY_ALERT_THRESHOLD,
            "accuracy_velocity": accuracy_velocity,
            "brier_trend":       brier_trend,
            "early_warnings":    early_warnings,
        }

        if flagged or early_warnings:
            logger.warning(
                "[performance-monitor] %d flagged, %d early-warning models: %s",
                len(flagged), len(early_warnings), flagged,
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
        """
        try:
            from sqlalchemy import select
            from app.modules.ai.models import ModelMetadata

            reweighted = False
            old_weight = None
            new_weight = None

            if source_name in orchestrator.model_meta:
                old_w = orchestrator.model_meta[source_name].get("weight", 1.0)
                if old_w > DRIFT_WEIGHT_HALVE_MIN * 2:
                    new_w = max(DRIFT_WEIGHT_HALVE_MIN, round(old_w * 0.5, 4))
                    orchestrator.model_meta[source_name]["weight"] = new_w
                    old_weight = old_w
                    new_weight = new_w
                    reweighted = True
                    logger.warning(
                        "[performance-monitor] DRIFT reweight: %s weight %.4f → %.4f (mag=%.4f)",
                        source_name, old_w, new_w, magnitude,
                    )

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
