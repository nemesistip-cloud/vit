"""
TRACK-007: Agent Workflow Manager — REST API
Exposes workflow dispatch, status, and statistics.

Prefix: /api/agents/workflow
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.modules.agents.workflow import WorkflowStatus, workflow_dispatcher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents/workflow", tags=["Agent Workflow"])


class SubmitTaskRequest(BaseModel):
    task_type: str = Field(..., description="Registered task type (e.g. prediction, settlement)")
    payload: Dict[str, Any] = Field(default_factory=dict)
    agent_id: Optional[str] = Field(None, description="Target a specific agent (optional)")
    priority: int = Field(5, ge=1, le=10)
    max_retries: int = Field(3, ge=0, le=10)
    timeout_s: float = Field(30.0, ge=1.0, le=300.0)


@router.post("/submit")
async def submit_workflow_task(
    body: SubmitTaskRequest,
    _: Any = Depends(get_current_user),
):
    """Submit a task to the agent workflow dispatcher."""
    task = await workflow_dispatcher.submit(
        task_type=body.task_type,
        payload=body.payload,
        agent_id=body.agent_id,
        priority=body.priority,
        max_retries=body.max_retries,
        timeout_s=body.timeout_s,
    )
    return {"task_id": task.task_id, "status": task.status.value}


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    _: Any = Depends(get_current_user),
):
    """Poll the status and result of a submitted workflow task."""
    task = workflow_dispatcher.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task.to_dict()


@router.get("/tasks")
async def list_workflow_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    task_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _: Any = Depends(get_current_user),
):
    """List recent workflow tasks with optional filters."""
    ws = WorkflowStatus(status) if status else None
    return {
        "tasks": workflow_dispatcher.list_tasks(status=ws, task_type=task_type, limit=limit)
    }


@router.get("/stats")
async def get_workflow_stats():
    """Return dispatcher statistics — handler performance, queue depth."""
    return workflow_dispatcher.get_stats()


@router.delete("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    _: Any = Depends(get_current_user),
):
    """Cancel a pending workflow task."""
    task = workflow_dispatcher.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in (WorkflowStatus.PENDING, WorkflowStatus.RETRYING):
        raise HTTPException(status_code=409, detail=f"Cannot cancel task in status '{task.status}'")
    task.status = WorkflowStatus.CANCELLED
    return {"task_id": task_id, "status": "cancelled"}
