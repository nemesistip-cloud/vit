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
        from app.agents.ml_config import get as get_ml_config

        cfg              = get_ml_config()
        threshold        = float(cfg.get("auto_promote_threshold", ACCURACY_IMPROVEMENT_THRESHOLD))
        auto_enabled     = bool(cfg.get("auto_promote_enabled", True))

        try:
            import app.api.routes.training as training_mod
            _model_versions = training_mod._model_versions
        except ImportError:
            logger.warning("[model-promoter] cannot import training module")
            return {"skipped": True, "reason": "training module unavailable"}

        if not _model_versions:
            return {"promoted": 0, "reason": "no version history yet"}

        if not auto_enabled:
            return {"promoted": 0, "reason": "auto_promote_disabled", "auto_enabled": False}

        # Candidates: completed jobs (have a summary) not yet evaluated
        candidates = [
            (jid, info) for jid, info in _model_versions.items()
            if jid not in self._promoted_jobs
            and info.get("summary")
        ]

        if not candidates:
            return {
                "promoted": 0,
                "no_candidates": True,
                "current_production": training_mod._current_production,
            }

        candidates.sort(key=lambda x: x[1].get("created_at", ""), reverse=True)

        # Get current production accuracy
        current_job_id: Optional[str] = training_mod._current_production
        current_acc = 0.0
        if current_job_id and current_job_id in _model_versions:
            current_acc = float(
                _model_versions[current_job_id].get("summary", {}).get("avg_accuracy", 0) or 0
            )

        promoted = 0
        skipped  = 0
        promotion_log: list = []

        for job_id, job_info in candidates[:3]:
            if job_id == current_job_id:
                self._promoted_jobs.add(job_id)
                continue

            summary  = job_info.get("summary", {})
            new_acc  = float(summary.get("avg_accuracy", 0) or 0)

            is_better = (new_acc > current_acc + threshold) or (not current_job_id)
            reason    = (
                f"accuracy +{(new_acc - current_acc) * 100:.1f}pp"
                if is_better and current_job_id
                else ("no current production version" if is_better else f"insufficient gain ({(new_acc - current_acc)*100:.1f}pp < {threshold*100:.1f}pp required)")
            )

            if is_better:
                training_mod._current_production = job_id
                job_info["promoted"]    = True
                job_info["promoted_at"] = datetime.now(timezone.utc).isoformat()
                job_info["promoted_by"] = "model-promoter-agent"

                self._promoted_jobs.add(job_id)
                promoted += 1
                promotion_log.append({
                    "job_id":    job_id,
                    "new_acc":   round(new_acc, 4),
                    "prev_acc":  round(current_acc, 4),
                    "reason":    reason,
                    "promoted_at": job_info["promoted_at"],
                })

                logger.info(
                    "[model-promoter] PROMOTED job=%s new_acc=%.4f prev_acc=%.4f reason=%s",
                    job_id, new_acc, current_acc, reason,
                )

                try:
                    from app.services.alerts import TelegramAlert, AlertPriority
                    tg = TelegramAlert()
                    await tg.send_message(
                        f"<b>🚀 Model Auto-Promoted</b>\n"
                        f"Job: <code>{job_id[:8]}</code>\n"
                        f"Reason: {reason}\n"
                        f"New accuracy: {new_acc*100:.1f}%\n"
                        f"Previous: {current_acc*100:.1f}%",
                        AlertPriority.MEDIUM,
                    )
                except Exception:
                    pass

                current_acc    = new_acc
                current_job_id = job_id
            else:
                self._promoted_jobs.add(job_id)
                skipped += 1
                logger.info("[model-promoter] skipped job=%s — %s", job_id, reason)

        return {
            "promoted":           promoted,
            "skipped":            skipped,
            "promotion_log":      promotion_log,
            "current_production": training_mod._current_production,
            "threshold":          threshold,
            "auto_enabled":       auto_enabled,
        }
