from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
from app.core.observability.manager import obs_manager
from app.core.observability.models import HealthStatus

router = APIRouter()

@router.get("/health", tags=["Observability"])
async def get_health():
    """Authoritative ecosystem health status."""
    status = obs_manager.health.get_overall_status()
    details = obs_manager.health.get_all_statuses()

    status_code = 200
    if status == HealthStatus.UNHEALTHY:
        status_code = 503
    elif status == HealthStatus.DEGRADED:
        status_code = 200 # Still operational

    # Use model_dump(mode='json') so that datetime fields are serialized to
    # ISO-8601 strings — plain s.dict() returns native datetime objects which
    # json.dumps (used internally by JSONResponse) cannot handle.
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status.value if hasattr(status, "value") else status,
            "subsystems": [s.model_dump(mode="json") for s in details],
        }
    )

@router.get("/live", tags=["Observability"])
async def get_liveness():
    """Liveness probe: returns 200 if the process is alive."""
    return {"status": "alive"}

@router.get("/ready", tags=["Observability"])
async def get_readiness():
    """Readiness probe: returns 200 if the platform is ready to serve requests."""
    status = obs_manager.health.get_overall_status()
    if status == HealthStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail="System not ready")
    return {"status": "ready"}

@router.get("/status", tags=["Observability"])
async def get_status():
    """Expose operational state summary."""
    return obs_manager.health.get_overall_status()

@router.get("/metrics", tags=["Observability"])
async def get_metrics():
    """Retrieve near real-time platform metrics."""
    return obs_manager.metrics.get_snapshot()

@router.get("/diagnostics", tags=["Observability"])
async def get_diagnostics():
    """Generate a comprehensive system diagnostics report."""
    return obs_manager.get_diagnostics()

@router.get("/alerts", tags=["Observability"])
async def get_alerts():
    """Retrieve active system alerts."""
    return obs_manager.alerts.get_active_alerts()

@router.get("/audit", tags=["Observability"])
async def get_audit_logs(limit: int = 50):
    """Retrieve recent audit logs (Requires Admin Authorization in production)."""
    # Authorization check should be added here
    return obs_manager.audit.get_records(limit=limit)
