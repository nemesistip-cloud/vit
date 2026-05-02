"""app/api/routes/agents.py — Autonomous agent status & control endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from app.api.middleware.auth import verify_api_key

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/status")
async def agents_status(_user=Depends(verify_api_key)):
    """Full status snapshot for all autonomous agents."""
    try:
        from app.agents.coordinator import get_coordinator
        return get_coordinator().status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/summary")
async def agents_summary(_user=Depends(verify_api_key)):
    """Lightweight one-row-per-agent health summary."""
    try:
        from app.agents.coordinator import get_coordinator
        return get_coordinator().summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/trigger/{agent_name}")
async def trigger_agent(agent_name: str, _user=Depends(verify_api_key)):
    """Manually trigger an agent's next cycle immediately."""
    try:
        from app.agents.coordinator import get_coordinator
        ok = get_coordinator().trigger(agent_name)
        if not ok:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{agent_name}' not found. "
                       f"Valid names: performance-monitor, weight-optimizer, retrain-trigger",
            )
        return {"triggered": agent_name, "status": "dispatched"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
