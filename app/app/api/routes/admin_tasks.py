"""Admin task management — /admin/tasks endpoints consumed by the admin panel.

The public task system lives at /api/tasks (app/modules/tasks/routes.py).
This router exposes an admin-friendly wrapper at /admin/tasks with:
  - A combined GET that returns {tasks, categories} in one call
  - Field-name mapping between the admin form (name/is_active/reset_frequency)
    and the DB model (title/status/task_type)
  - PUT support (admin.tsx uses apiPut, not apiPatch)
  - A completions list endpoint for the Recent Completions table
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.modules.tasks.models import Task, TaskCategory, TaskStatus, UserTaskCompletion
from app.modules.tasks.service import TaskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/tasks", tags=["Admin Tasks"])


def _require_admin(user: User) -> None:
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")


def _reset_freq_to_task_type(freq: str) -> str:
    return {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}.get(freq, "one_time")


def _task_type_to_reset_freq(task_type: str) -> str:
    return task_type if task_type in ("daily", "weekly", "monthly") else "never"


def _task_to_admin(task: Task, completion_count: int = 0) -> Dict[str, Any]:
    reqs = task.requirements or {}
    return {
        "id": task.id,
        "name": task.title,
        "description": task.description,
        "category_id": task.category_id,
        "xp_reward": task.xp_reward,
        "vit_reward": float(task.vit_reward or 0),
        "trigger_type": reqs.get("trigger_type", "manual"),
        "trigger_condition": reqs.get("trigger_condition", ""),
        "max_completions": task.max_completions,
        "is_active": (task.status == TaskStatus.ACTIVE.value if isinstance(task.status, str)
                      else task.status == TaskStatus.ACTIVE),
        "reset_frequency": _task_type_to_reset_freq(
            task.task_type if isinstance(task.task_type, str) else task.task_type.value
        ),
        "completion_count": completion_count,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


class AdminTaskRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    category_id: Any
    xp_reward: int = 0
    vit_reward: float = 0
    trigger_type: str = "manual"
    trigger_condition: str = ""
    max_completions: Optional[int] = None
    is_active: bool = True
    reset_frequency: str = "never"


@router.get("")
async def list_admin_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _require_admin(current_user)

    tasks_result = await db.execute(
        select(Task).options(selectinload(Task.category)).order_by(Task.created_at.desc())
    )
    tasks = list(tasks_result.scalars().all())

    counts_result = await db.execute(
        select(UserTaskCompletion.task_id, func.count(UserTaskCompletion.id))
        .where(UserTaskCompletion.is_completed == True)
        .group_by(UserTaskCompletion.task_id)
    )
    counts: Dict[int, int] = {row[0]: row[1] for row in counts_result.all()}

    cats_result = await db.execute(
        select(TaskCategory).order_by(TaskCategory.sort_order, TaskCategory.name)
    )
    categories = list(cats_result.scalars().all())

    return {
        "tasks": [_task_to_admin(t, counts.get(t.id, 0)) for t in tasks],
        "categories": [
            {"id": c.id, "name": c.name, "description": c.description,
             "icon": c.icon, "color": c.color, "sort_order": c.sort_order}
            for c in categories
        ],
    }


@router.get("/completions")
async def list_admin_task_completions(
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _require_admin(current_user)

    result = await db.execute(
        select(UserTaskCompletion)
        .options(selectinload(UserTaskCompletion.user), selectinload(UserTaskCompletion.task))
        .where(UserTaskCompletion.is_completed == True)
        .order_by(UserTaskCompletion.last_completed_at.desc())
        .limit(limit)
    )
    completions = list(result.scalars().all())

    total_result = await db.execute(
        select(func.count(UserTaskCompletion.id)).where(UserTaskCompletion.is_completed == True)
    )
    total = total_result.scalar() or 0

    return {
        "completions": [
            {
                "id": c.id,
                "user_id": c.user_id,
                "username": (c.user.username if c.user else None),
                "task_id": c.task_id,
                "task_name": (c.task.title if c.task else None),
                "total_vit_earned": float(c.total_vit_earned or 0),
                "total_xp_earned": c.total_xp_earned,
                "last_completed_at": (
                    c.last_completed_at.isoformat() if c.last_completed_at else None
                ),
            }
            for c in completions
        ],
        "total": total,
    }


@router.post("")
async def create_admin_task(
    request: AdminTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _require_admin(current_user)

    category_id = int(request.category_id)
    category = await TaskService.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Task category not found")

    task_type = _reset_freq_to_task_type(request.reset_frequency)
    requirements: Dict[str, Any] = {}
    if request.trigger_type and request.trigger_type != "manual":
        requirements["trigger_type"] = request.trigger_type
    if request.trigger_condition:
        requirements["trigger_condition"] = request.trigger_condition

    status = TaskStatus.ACTIVE.value if request.is_active else TaskStatus.INACTIVE.value

    task = await TaskService.create_task(
        db=db,
        category_id=category_id,
        title=request.name,
        description=request.description,
        task_type=task_type,
        vit_reward=Decimal(str(request.vit_reward)),
        xp_reward=request.xp_reward,
        created_by=current_user.id,
        max_completions=request.max_completions or 1,
        requirements=requirements,
        status=status,
        updated_at=datetime.now(timezone.utc),
    )
    return _task_to_admin(task)


@router.put("/{task_id}")
async def update_admin_task(
    task_id: int,
    request: AdminTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _require_admin(current_user)

    task = await TaskService.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task_type = _reset_freq_to_task_type(request.reset_frequency)
    requirements: Dict[str, Any] = {}
    if request.trigger_type and request.trigger_type != "manual":
        requirements["trigger_type"] = request.trigger_type
    if request.trigger_condition:
        requirements["trigger_condition"] = request.trigger_condition

    updates = {
        "title": request.name,
        "description": request.description,
        "category_id": int(request.category_id),
        "xp_reward": request.xp_reward,
        "vit_reward": Decimal(str(request.vit_reward)),
        "task_type": task_type,
        "max_completions": request.max_completions or 1,
        "requirements": requirements,
        "status": TaskStatus.ACTIVE.value if request.is_active else TaskStatus.INACTIVE.value,
    }
    task = await TaskService.update_task(db, task_id, updates)
    return _task_to_admin(task)


@router.delete("/{task_id}")
async def delete_admin_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _require_admin(current_user)

    result = await db.execute(sa_delete(Task).where(Task.id == task_id))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}


@router.post("/reset-expired")
async def reset_expired_admin_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _require_admin(current_user)
    reset_count = await TaskService.reset_expired_tasks(db)
    return {"reset_count": reset_count}
