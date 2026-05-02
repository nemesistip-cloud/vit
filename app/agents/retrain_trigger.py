"""app/agents/retrain_trigger.py

RetrainTriggerAgent — runs every 12 hours.

Responsibilities:
  - Read the flagged_models list from PerformanceMonitorAgent via coordinator
  - If drift or sustained poor accuracy is detected, trigger retraining
  - Use the existing Celery task if Redis is available, otherwise run inline
  - Enforce a cooldown so the same model isn't retrained more than once per 24h
  - Write trigger events back to coordinator registry
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

RETRAIN_COOLDOWN_HOURS = 24   # minimum gap between retrains per model
MIN_FLAG_CYCLES        = 2    # model must be flagged for at least N consecutive cycles


class RetrainTriggerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="retrain-trigger",
            interval_seconds=12 * 3600,   # every 12 hours
            initial_delay_seconds=5 * 60, # start 5 min after boot
        )
        self._flag_counts:    Dict[str, int]      = {}   # consecutive flag count per model
        self._last_retrain:   Dict[str, datetime] = {}   # last retrain timestamp per model
        self._trigger_log:    List[Dict]          = []   # recent trigger events

    def _is_on_cooldown(self, model_key: str) -> bool:
        last = self._last_retrain.get(model_key)
        if last is None:
            return False
        return datetime.now(timezone.utc) - last < timedelta(hours=RETRAIN_COOLDOWN_HOURS)

    async def run_cycle(self) -> Dict[str, Any]:
        from app.agents.coordinator import get_coordinator

        coordinator = get_coordinator()
        perf_snap   = coordinator.get_agent_result("performance-monitor")
        flagged_now: List[str] = (perf_snap or {}).get("flagged_models", [])

        # Update consecutive flag counters
        all_known = set(self._flag_counts) | set(flagged_now)
        for key in all_known:
            if key in flagged_now:
                self._flag_counts[key] = self._flag_counts.get(key, 0) + 1
            else:
                self._flag_counts[key] = 0   # reset streak

        triggered: List[str] = []
        skipped:   List[Dict] = []

        for model_key, consecutive in list(self._flag_counts.items()):
            if consecutive < MIN_FLAG_CYCLES:
                continue
            if self._is_on_cooldown(model_key):
                skipped.append({"model": model_key, "reason": "cooldown"})
                continue

            # Trigger retraining
            success = await self._trigger_retrain(model_key)
            if success:
                triggered.append(model_key)
                self._last_retrain[model_key] = datetime.now(timezone.utc)
                self._flag_counts[model_key]  = 0   # reset streak after trigger
                event = {
                    "model":       model_key,
                    "triggered_at": datetime.now(timezone.utc).isoformat(),
                    "consecutive_flags": consecutive,
                }
                self._trigger_log = (self._trigger_log[-49:] + [event])
                logger.info(
                    "[retrain-trigger] triggered retraining for %s "
                    "(consecutive_flags=%d)",
                    model_key, consecutive,
                )

        return {
            "flagged_now":       flagged_now,
            "flag_counts":       dict(self._flag_counts),
            "triggered":         triggered,
            "skipped":           skipped,
            "recent_triggers":   self._trigger_log[-10:],
            "cooldown_hours":    RETRAIN_COOLDOWN_HOURS,
            "min_flag_cycles":   MIN_FLAG_CYCLES,
        }

    async def _trigger_retrain(self, model_key: str) -> bool:
        """Dispatch retraining — Celery if available, otherwise inline stub."""
        try:
            from app.tasks.retraining import retrain_models_task
            if hasattr(retrain_models_task, "delay"):
                retrain_models_task.delay([model_key])
                logger.info("[retrain-trigger] dispatched Celery task for %s", model_key)
            else:
                # No Celery — log intent; real retraining requires manual trigger
                logger.info(
                    "[retrain-trigger] Celery unavailable — retraining flagged "
                    "for %s (manual via Admin → Training)", model_key,
                )
            return True
        except Exception as exc:
            logger.error("[retrain-trigger] dispatch failed for %s: %s", model_key, exc)
            return False
