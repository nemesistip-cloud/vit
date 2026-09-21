"""
app/modules/agents/router.py — Agent module-level router (TRACK-007).

Exposes HTTP endpoints that wrap the WorkflowDispatcher singleton defined in
app.modules.agents.workflow.  The primary agent-workflow API lives at
app/api/routes/agent_workflow.py; this module-level router makes the agents
module self-contained and provides a lightweight status/health surface.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.modules.agents.workflow import WorkflowStatus, workflow_dispatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["Agents"])


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class SubmitTaskRequest(BaseModel):
    task_type: str = Field(..., description="Registered task type, e.g. prediction, settlement")
    payload: Dict[str, Any] = Field(default_factory=dict)
    agent_id: Optional[str] = Field(None, description="Target a specific agent (optional)")
    priority: int = Field(5, ge=1, le=10)
    max_retries: int = Field(3, ge=0, le=10)
    timeout_s: float = Field(30.0, ge=1.0, le=300.0)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", summary="Agents module info")
async def agents_info():
    """Return basic module metadata."""
    return {"module": "agents", "status": "operational", "version": "1.0"}


@router.get("/health", include_in_schema=False)
async def agents_health():
    return {"status": "ok"}


@router.get("/dispatcher/stats", summary="Workflow dispatcher statistics")
async def dispatcher_stats():
    """Return live dispatcher stats: queue depth, handler performance, task counts."""
    return workflow_dispatcher.get_stats()


@router.post("/workflow/submit", summary="Submit a workflow task")
async def submit_task(
    body: SubmitTaskRequest,
    _: Any = Depends(get_current_user),
):
    """Submit a task to the agent workflow dispatcher and return its task_id."""
    task = await workflow_dispatcher.submit(
        task_type=body.task_type,
        payload=body.payload,
        agent_id=body.agent_id,
        priority=body.priority,
        max_retries=body.max_retries,
        timeout_s=body.timeout_s,
    )
    return {"task_id": task.task_id, "status": task.status.value}


@router.get("/workflow/tasks", summary="List workflow tasks")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by WorkflowStatus"),
    task_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _: Any = Depends(get_current_user),
):
    """List recent workflow tasks with optional status / type filters."""
    ws = WorkflowStatus(status) if status else None
    return {
        "tasks": workflow_dispatcher.list_tasks(
            status=ws, task_type=task_type, limit=limit
        )
    }


@router.get("/workflow/tasks/{task_id}", summary="Get task status")
async def get_task(
    task_id: str,
    _: Any = Depends(get_current_user),
):
    """Poll the status and result of a submitted workflow task."""
    task = workflow_dispatcher.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found")
    return task.to_dict()


@router.delete("/workflow/tasks/{task_id}/cancel", summary="Cancel a pending task")
async def cancel_task(
    task_id: str,
    _: Any = Depends(get_current_user),
):
    """Cancel a PENDING or RETRYING workflow task."""
    task = workflow_dispatcher.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in (WorkflowStatus.PENDING, WorkflowStatus.RETRYING):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel task in status {task.status!r}",
        )
    task.status = WorkflowStatus.CANCELLED
    return {"task_id": task_id, "status": "cancelled"}
