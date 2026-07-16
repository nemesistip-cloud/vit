# app/tasks/retraining.py
"""
Retraining task — runs scripts/train_models.py in a subprocess.

Works whether Celery is available or not:
  - With Celery   : dispatched as a background Celery task via .delay()
  - Without Celery: runs inline via asyncio.create_subprocess_exec()
    (called from RetrainTriggerAgent and the /api/admin/retrain endpoint)

The subprocess writes model .pkl files to /models/ which the orchestrator
picks up on the next prediction request (no restart required).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
TRAIN_SCRIPT = ROOT / "scripts" / "train_models.py"
PYTHON = sys.executable


async def run_training_subprocess(model_names: list[str] | None = None) -> dict:
    """
    Run scripts/train_models.py asynchronously in a subprocess.

    Returns a dict with keys: status, returncode, stdout_tail, started_at, finished_at.
    Non-zero returncode means the training script itself failed — logs are preserved.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    cmd = [PYTHON, str(TRAIN_SCRIPT)]

    logger.info("[retrain] Starting training subprocess: %s", " ".join(cmd))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(ROOT),
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )

        lines: list[str] = []
        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip()
            lines.append(line)
            logger.info("[retrain-out] %s", line)

        await proc.wait()
        finished_at = datetime.now(timezone.utc).isoformat()
        tail = "\n".join(lines[-20:]) if lines else "(no output)"

        if proc.returncode == 0:
            logger.info("[retrain] Training completed successfully (rc=0)")
            return {
                "status": "completed",
                "returncode": 0,
                "stdout_tail": tail,
                "started_at": started_at,
                "finished_at": finished_at,
                "models": model_names or ["all"],
            }
        else:
            logger.error("[retrain] Training script exited with rc=%d", proc.returncode)
            return {
                "status": "failed",
                "returncode": proc.returncode,
                "stdout_tail": tail,
                "started_at": started_at,
                "finished_at": finished_at,
                "models": model_names or ["all"],
            }

    except Exception as exc:
        logger.error("[retrain] Subprocess launch failed: %s", exc)
        return {
            "status": "error",
            "returncode": -1,
            "error": str(exc),
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "models": model_names or ["all"],
        }


# ── Celery task (used when Redis + Celery worker is available) ─────────────────

try:
    from celery import shared_task

    @shared_task(name="retrain_models_task", bind=True, max_retries=1)
    def retrain_models_task(self, model_names: list | None = None):
        """Celery-wrapped training task — runs the training subprocess synchronously."""
        logger.info("[retrain-celery] Task received for models: %s", model_names or "all")
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(run_training_subprocess(model_names))
        finally:
            loop.close()
        if result["status"] == "failed":
            raise RuntimeError(
                f"Training script exited rc={result['returncode']}\n{result['stdout_tail']}"
            )
        return result

    @shared_task(name="check_model_drift_task")
    def check_model_drift_task():
        logger.info("[retrain-celery] Drift check task received")
        return {"drift_detected": False, "timestamp": datetime.now(timezone.utc).isoformat()}

except ImportError:
    # No Celery installed — provide a compatible shim so existing callers
    # (retrain_trigger.py checks hasattr(task, 'delay')) still work.

    class _AsyncShimTask:
        """
        Shim that exposes .delay() like a Celery task but fires an asyncio
        subprocess in the running event loop.
        """
        def delay(self, model_names: list | None = None):
            logger.info(
                "[retrain-shim] Celery unavailable — scheduling inline training "
                "for models: %s", model_names or "all"
            )
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(run_training_subprocess(model_names))
                else:
                    loop.run_until_complete(run_training_subprocess(model_names))
            except Exception as exc:
                logger.warning("[retrain-shim] Could not schedule training: %s", exc)

    retrain_models_task = _AsyncShimTask()
    check_model_drift_task = _AsyncShimTask()
