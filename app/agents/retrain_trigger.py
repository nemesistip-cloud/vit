"""app/agents/retrain_trigger.py

RetrainTriggerAgent — runs every 12 hours.

Responsibilities:
  - Read the flagged_models list from PerformanceMonitorAgent via coordinator
  - If drift or sustained poor accuracy is detected, trigger retraining
  - Use the existing Celery task if Redis is available, otherwise run inline
  - Enforce a cooldown so the same model isn't retrained more than once per 24h
  - Write trigger events back to coordinator registry
  - P0#3 / P1#7: After a successful retrain, call calibration.fit_from_history()
    when ≥ AUTO_CALIBRATE_MIN_SAMPLES settled matches exist in the DB
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

AUTO_CALIBRATE_MIN_SAMPLES = 30  # minimum settled matches before auto-calibration


class RetrainTriggerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="retrain-trigger",
            interval_seconds=12 * 3600,
            initial_delay_seconds=5 * 60,
        )
        self._flag_counts:    Dict[str, int]      = {}
        self._last_retrain:   Dict[str, datetime] = {}
        self._trigger_log:    List[Dict]          = []
        self._triggered_jobs: Dict[str, str]      = {}  # model_key → job_id
        self._last_calibration_at: Optional[datetime] = None

    def _is_on_cooldown(self, model_key: str, cooldown_hours: int) -> bool:
        last = self._last_retrain.get(model_key)
        if last is None:
            return False
        return datetime.now(timezone.utc) - last < timedelta(hours=cooldown_hours)

    async def run_cycle(self) -> Dict[str, Any]:
        from app.agents.coordinator import get_coordinator
        from app.agents.ml_config import get as get_ml_config

        cfg             = get_ml_config()
        cooldown_hours  = int(cfg.get("retrain_cooldown_hours", 24))
        min_flag_cycles = int(cfg.get("min_flag_cycles", 2))
        auto_enabled    = bool(cfg.get("auto_retrain_enabled", True))

        coordinator = get_coordinator()
        perf_snap   = coordinator.get_agent_result("performance-monitor")
        flagged_now: List[str] = (perf_snap or {}).get("flagged_models", [])

        all_known = set(self._flag_counts) | set(flagged_now)
        for key in all_known:
            if key in flagged_now:
                self._flag_counts[key] = self._flag_counts.get(key, 0) + 1
            else:
                self._flag_counts[key] = 0

        triggered: List[str] = []
        skipped:   List[Dict] = []

        if not auto_enabled:
            return {
                "flagged_now":     flagged_now,
                "flag_counts":     dict(self._flag_counts),
                "triggered":       [],
                "skipped":         [{"model": k, "reason": "auto_retrain_disabled"} for k in self._flag_counts if self._flag_counts[k] >= min_flag_cycles],
                "recent_triggers": self._trigger_log[-10:],
                "triggered_jobs":  dict(self._triggered_jobs),
                "cooldown_hours":  cooldown_hours,
                "min_flag_cycles": min_flag_cycles,
                "auto_enabled":    False,
            }

        for model_key, consecutive in list(self._flag_counts.items()):
            if consecutive < min_flag_cycles:
                continue
            if self._is_on_cooldown(model_key, cooldown_hours):
                skipped.append({"model": model_key, "reason": "cooldown"})
                continue

            success, job_id = await self._trigger_retrain(model_key)
            if success:
                triggered.append(model_key)
                self._last_retrain[model_key] = datetime.now(timezone.utc)
                self._flag_counts[model_key]  = 0
                if job_id:
                    self._triggered_jobs[model_key] = job_id
                event = {
                    "model":             model_key,
                    "triggered_at":      datetime.now(timezone.utc).isoformat(),
                    "consecutive_flags": consecutive,
                    "job_id":            job_id,
                }
                self._trigger_log = self._trigger_log[-49:] + [event]
                logger.info(
                    "[retrain-trigger] triggered retraining for %s "
                    "(consecutive=%d) job_id=%s",
                    model_key, consecutive, job_id,
                )

        # ── P0#3 / P1#7: Auto-calibration after retraining ────────────────────
        calibration_result = None
        if triggered:
            calibration_result = await self._auto_calibrate_if_ready()

        return {
            "flagged_now":       flagged_now,
            "flag_counts":       dict(self._flag_counts),
            "triggered":         triggered,
            "skipped":           skipped,
            "recent_triggers":   self._trigger_log[-10:],
            "triggered_jobs":    dict(self._triggered_jobs),
            "cooldown_hours":    cooldown_hours,
            "min_flag_cycles":   min_flag_cycles,
            "auto_enabled":      auto_enabled,
            "calibration_result": calibration_result,
        }

    async def _trigger_retrain(self, model_key: str) -> tuple[bool, Optional[str]]:
        """Fire a real training job — direct async call, no Celery required."""
        try:
            from app.api.routes.training import TrainingConfig, start_admin_training_request

            target_keys: Optional[List[str]] = None
            if model_key and model_key not in ("__all__", "all"):
                target_keys = [model_key]

            config = TrainingConfig(
                target_model_keys=target_keys,
                note=f"Autonomous retrain triggered by performance-monitor "
                     f"(accuracy drift · model={model_key})",
            )
            result = await start_admin_training_request(
                config, created_by="retrain-trigger-agent"
            )
            job_id = result.get("job_id")
            logger.info("[retrain-trigger] training job started: %s for model=%s", job_id, model_key)
            return True, job_id

        except Exception as exc:
            logger.error("[retrain-trigger] start_admin_training_request failed for %s: %s", model_key, exc)
            # Unknown model key → fallback to full ensemble retrain
            if "Unknown model key" in str(exc):
                try:
                    from app.api.routes.training import TrainingConfig, start_admin_training_request
                    result = await start_admin_training_request(
                        TrainingConfig(note=f"Auto-retrain fallback (unknown key={model_key})"),
                        created_by="retrain-trigger-agent",
                    )
                    return True, result.get("job_id")
                except Exception as exc2:
                    logger.error("[retrain-trigger] fallback full retrain also failed: %s", exc2)
            return False, None

    async def _auto_calibrate_if_ready(self) -> Optional[Dict]:
        """
        P0#3 / P1#7: Automatically run calibration.fit_from_history() when:
        1. At least AUTO_CALIBRATE_MIN_SAMPLES settled matches exist.
        2. Calibration was not run in the last 6 hours (avoid thrashing).
        """
        now = datetime.now(timezone.utc)
        if (self._last_calibration_at is not None and
                now - self._last_calibration_at < timedelta(hours=6)):
            logger.debug("[retrain-trigger] calibration skipped — cooldown active")
            return {"skipped": True, "reason": "cooldown"}

        try:
            from app.db.database import AsyncSessionLocal
            from app.services.calibration import fit_from_history
            from sqlalchemy import select, func
            from app.db.models import Match

            async with AsyncSessionLocal() as db:
                count_res = await db.execute(
                    select(func.count(Match.id)).where(Match.actual_outcome.isnot(None))
                )
                n_settled = count_res.scalar_one_or_none() or 0

                if n_settled < AUTO_CALIBRATE_MIN_SAMPLES:
                    logger.info(
                        "[retrain-trigger] auto-calibration skipped — "
                        "only %d settled matches (need %d)",
                        n_settled, AUTO_CALIBRATE_MIN_SAMPLES,
                    )
                    return {"skipped": True, "reason": "insufficient_samples", "n_settled": n_settled}

                logger.info(
                    "[retrain-trigger] running auto-calibration on %d settled matches…",
                    n_settled,
                )
                report = await fit_from_history(db, method="both", min_samples=10)
                self._last_calibration_at = now
                logger.info(
                    "[retrain-trigger] auto-calibration complete: %d models fitted",
                    len(report.get("models_fitted", {})),
                )
                return {
                    "skipped":       False,
                    "n_settled":     n_settled,
                    "models_fitted": list(report.get("models_fitted", {}).keys()),
                    "triggered_at":  now.isoformat(),
                }
        except Exception as exc:
            logger.error("[retrain-trigger] auto-calibration failed: %s", exc)
            return {"skipped": True, "reason": "error", "error": str(exc)}
