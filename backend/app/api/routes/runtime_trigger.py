"""
app/api/routes/runtime_trigger.py

External trigger & runtime observability router for Render Free Plan compatibility.
Allows external schedulers (e.g. GitHub Actions or free cron) to wake VITNetwork,
inspect service diagnostics, and trigger on-demand job execution selectively without
continuous cross-service pinging.
"""

import time
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.db.models import JobCheckpoint, Match, Prediction
from app.core.runtime.service_registry import service_registry, ServiceState
from app.core.runtime.service_client import SleepResilientClient
from app.services.settlement_service import run_auto_settlement
from app.config import get_env

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/runtime", tags=["Runtime Manager"])

def _verify_trigger_auth(x_trigger_token: Optional[str] = Header(None)) -> None:
    expected_token = get_env("RUNTIME_TRIGGER_TOKEN", "")
    if expected_token and x_trigger_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Trigger-Token header."
        )

@router.get("/status", response_model=Dict[str, Any])
async def get_runtime_status() -> Dict[str, Any]:
    """Return observability snapshot including service state, last check, and failure states."""
    diagnostics = service_registry.get_diagnostics()
    return {
        "timestamp": time.time(),
        "runtime": "VITNetwork Gateway",
        "diagnostics": diagnostics
    }

@router.post("/trigger", response_model=Dict[str, Any])
async def trigger_runtime_scheduler(
    job_key: Optional[str] = Query(None, description="Specific job key to trigger"),
    reconcile_sports: bool = Query(True, description="Whether to reconcile live sports state on wake"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_trigger_auth)
) -> Dict[str, Any]:
    """
    Sleep-aware external scheduler invocation endpoint.
    Determines which background jobs need execution after wake-up.
    """
    start_time = time.time()
    results: Dict[str, Any] = {
        "executed_jobs": [],
        "reconciled_sports": False,
        "settled_matches": 0,
        "errors": []
    }

    # 1. Reconcile Live Sports State upon wake
    if reconcile_sports:
        try:
            from app.services.live_match_ingestion import LiveMatchIngestionService
            ingestion_service = LiveMatchIngestionService(db)
            res = await ingestion_service.sync_live_matches()
            results["reconciled_sports"] = True
            results["live_sync_details"] = res
        except Exception as exc:
            logger.error(f"[RuntimeTrigger] Live sports reconciliation failed: {exc}", exc_info=True)
            results["errors"].append(f"Sports reconciliation: {str(exc)}")

    # 2. Run Auto-Settlement Job with Checkpointing
    try:
        settlement_res = await run_auto_settlement(db)
        settled = settlement_res.get("settled_matches", 0)
        results["settled_matches"] = settled
        results["executed_jobs"].append("settlement")

        # Save Checkpoint in DB
        stmt = select(JobCheckpoint).where(JobCheckpoint.job_key == "auto_settlement")
        res = await db.execute(stmt)
        checkpoint = res.scalar_one_or_none()
        if not checkpoint:
            checkpoint = JobCheckpoint(job_key="auto_settlement", task_name="settlement")
            db.add(checkpoint)

        checkpoint.status = "COMPLETED"
        checkpoint.run_count = (checkpoint.run_count or 0) + 1
        checkpoint.last_checkpoint_data = f"{{\"settled_matches\": {settled}}}"
        await db.commit()

    except Exception as exc:
        logger.error(f"[RuntimeTrigger] Settlement task failed: {exc}", exc_info=True)
        results["errors"].append(f"Settlement: {str(exc)}")

    results["duration_seconds"] = round(time.time() - start_time, 3)
    return results
