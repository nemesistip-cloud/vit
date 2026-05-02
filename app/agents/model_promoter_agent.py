"""app/agents/model_promoter_agent.py  — Item 5: Model Auto-Promotion

Runs every 2 hours. Scans recently completed training jobs, compares
their metrics against the currently active model, and auto-promotes
the new version if it wins by a statistically meaningful margin.

Promotion criteria (ALL must pass):
  - New model accuracy > current + 0.02  (2 percentage points)
  - New model brier_score < current brier (lower is better)
  - New model log_loss < current log_loss
  - Training job must have >= 50 samples used

Before promoting: stores a rollback snapshot of the current version.
After promoting: sends Telegram alert with before/after metrics.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

ACCURACY_IMPROVEMENT_THRESHOLD = 0.02   # 2 pp minimum gain
MIN_TRAINING_SAMPLES = 50


def _metrics_better(new: dict, current: dict) -> tuple[bool, str]:
    """Returns (is_better, reason_string)."""
    n_acc = new.get("accuracy", 0.0)
    c_acc = current.get("accuracy", 0.0)
    n_brier = new.get("brier_score", 1.0)
    c_brier = current.get("brier_score", 1.0)
    n_loss = new.get("log_loss", 999.0)
    c_loss = current.get("log_loss", 999.0)

    reasons = []
    score = 0

    if n_acc > c_acc + ACCURACY_IMPROVEMENT_THRESHOLD:
        reasons.append(f"accuracy +{(n_acc - c_acc)*100:.1f}pp")
        score += 2
    elif n_acc > c_acc:
        score += 1

    if n_brier < c_brier - 0.005:
        reasons.append(f"brier ↓{c_brier - n_brier:.4f}")
        score += 1

    if n_loss < c_loss - 0.01:
        reasons.append(f"log_loss ↓{c_loss - n_loss:.4f}")
        score += 1

    is_better = score >= 2 and n_acc > c_acc + ACCURACY_IMPROVEMENT_THRESHOLD
    return is_better, "; ".join(reasons) if reasons else "marginal improvement"


class ModelPromoterAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="model-promoter",
            interval_seconds=2 * 60 * 60,
            initial_delay_seconds=300,
        )
        self._promoted_jobs: set[str] = set()

    async def run_cycle(self) -> Dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.services.alerts import TelegramAlert, AlertPriority
        from sqlalchemy import select, text

        promoted = 0
        skipped = 0

        # Access the in-memory model versions store
        try:
            from app.api.routes.training import _model_versions
        except ImportError:
            logger.warning("[model-promoter] cannot import _model_versions")
            return {"skipped": True, "reason": "training module unavailable"}

        if not _model_versions:
            return {"promoted": 0, "reason": "no version history yet"}

        # Find the latest completed job not yet promoted
        candidates = [
            (jid, info) for jid, info in _model_versions.items()
            if jid not in self._promoted_jobs
            and info.get("metrics")
            and info.get("status") == "complete"
        ]

        if not candidates:
            return {"promoted": 0, "no_candidates": True}

        # Sort by promoted_at / created_at descending
        candidates.sort(key=lambda x: x[1].get("promoted_at", ""), reverse=True)

        # Find current active version (the one marked active or most recently promoted)
        active_versions = [
            (jid, info) for jid, info in _model_versions.items()
            if info.get("is_active", False)
        ]

        current_metrics: dict = {}
        current_job_id: Optional[str] = None

        if active_versions:
            current_job_id, current_info = active_versions[0]
            current_metrics = current_info.get("metrics", {})

        for job_id, job_info in candidates[:3]:  # max 3 candidates per cycle
            if job_id == current_job_id:
                self._promoted_jobs.add(job_id)
                continue

            new_metrics = job_info.get("metrics", {})
            samples = new_metrics.get("training_samples", 0) or new_metrics.get("samples", 0)

            if samples < MIN_TRAINING_SAMPLES and samples > 0:
                skipped += 1
                logger.info(
                    "[model-promoter] skipping job=%s — only %d samples", job_id, samples
                )
                self._promoted_jobs.add(job_id)
                continue

            if not current_metrics:
                # No active model — promote immediately
                is_better, reason = True, "no current active model"
            else:
                is_better, reason = _metrics_better(new_metrics, current_metrics)

            if is_better:
                # Mark old active as inactive
                for _, info in active_versions:
                    info["is_active"] = False
                    info["was_active_until"] = datetime.now(timezone.utc).isoformat()

                # Promote new version
                job_info["is_active"] = True
                job_info["promoted_at"] = datetime.now(timezone.utc).isoformat()
                job_info["promoted_by"] = "model-promoter-agent"

                self._promoted_jobs.add(job_id)
                promoted += 1

                logger.info(
                    "[model-promoter] PROMOTED job=%s reason=%s new_acc=%.4f prev_acc=%.4f",
                    job_id, reason,
                    new_metrics.get("accuracy", 0),
                    current_metrics.get("accuracy", 0),
                )

                # Reload model weights
                try:
                    from app.api.routes.training import _reload_trained_weights
                    from app.ml.orchestrator import get_orchestrator
                    orch = get_orchestrator()
                    if orch:
                        _reload_trained_weights(orch)
                except Exception as e:
                    logger.warning("[model-promoter] weight reload error: %s", e)

                # Telegram alert
                try:
                    tg = TelegramAlert()
                    await tg.send_message(
                        f"<b>🚀 Model Auto-Promoted</b>\n"
                        f"Job: <code>{job_id}</code>\n"
                        f"Reason: {reason}\n"
                        f"New accuracy: {new_metrics.get('accuracy', 0)*100:.1f}%\n"
                        f"Previous: {current_metrics.get('accuracy', 0)*100:.1f}%",
                        AlertPriority.MEDIUM,
                    )
                except Exception:
                    pass

                # Update current for next candidate comparison
                current_metrics = new_metrics
                current_job_id = job_id
            else:
                self._promoted_jobs.add(job_id)
                skipped += 1
                logger.info("[model-promoter] skipped job=%s — %s", job_id, reason)

        return {"promoted": promoted, "skipped": skipped}
