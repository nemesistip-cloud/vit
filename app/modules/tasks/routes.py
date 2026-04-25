"""Task system REST API — Module T."""

import logging
from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.modules.tasks.models import Task, TaskCategory, UserTaskCompletion, TaskType, TaskStatus
from app.modules.tasks.service import TaskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class TaskCategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    sort_order: int
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: int
    category_id: int
    category: TaskCategoryResponse
    title: str
    description: str
    short_description: Optional[str]
    task_type: str
    status: str
    required_count: int
    max_completions: int
    vit_reward: float
    xp_reward: int
    expires_at: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    is_featured: bool
    requirements: dict
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class UserTaskCompletionResponse(BaseModel):
    id: int
    task_id: int
    task: TaskResponse
    current_progress: int
    required_progress: int
    is_completed: bool
    completed_count: int
    last_completed_at: Optional[str]
    next_reset_at: Optional[str]
    total_vit_earned: float
    total_xp_earned: int

    class Config:
        from_attributes = True


class CreateTaskCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    sort_order: int = 0


class CreateTaskRequest(BaseModel):
    category_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    short_description: Optional[str] = Field(None, max_length=100)
    task_type: str = Field(..., pattern="^(one_time|daily|weekly|monthly|progress)$")
    required_count: int = Field(1, ge=1)
    max_completions: int = Field(1, ge=1)
    vit_reward: float = Field(0, ge=0)
    xp_reward: int = Field(0, ge=0)
    expires_at: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    is_featured: bool = False
    requirements: dict = Field(default_factory=dict)
    action_url: Optional[str] = Field(None, max_length=200)
    action_label: Optional[str] = Field(None, max_length=50)


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    short_description: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, pattern="^(active|inactive|expired)$")
    required_count: Optional[int] = Field(None, ge=1)
    max_completions: Optional[int] = Field(None, ge=1)
    vit_reward: Optional[float] = Field(None, ge=0)
    xp_reward: Optional[int] = Field(None, ge=0)
    expires_at: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    is_featured: Optional[bool] = None
    requirements: Optional[dict] = None
    action_url: Optional[str] = Field(None, max_length=200)
    action_label: Optional[str] = Field(None, max_length=50)


class TaskStatsResponse(BaseModel):
    total_tasks_attempted: int
    total_completions: int
    total_vit_earned: float
    total_xp_earned: int


# ── Public endpoints ───────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[TaskCategoryResponse])
async def get_task_categories(db: AsyncSession = Depends(get_db)):
    """Get all active task categories."""
    categories = await TaskService.get_categories(db)
    return categories


@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    category_id: Optional[int] = None,
    featured_only: bool = False,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get available tasks."""
    tasks = await TaskService.get_tasks(
        db=db,
        category_id=category_id,
        featured_only=featured_only,
        limit=limit
    )
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific task."""
    task = await TaskService.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ── User endpoints ─────────────────────────────────────────────────────────────

@router.get("/user/progress", response_model=List[UserTaskCompletionResponse])
async def get_user_task_progress(
    completed_only: bool = False,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's task progress."""
    completions = await TaskService.get_user_task_completions(
        db=db,
        user_id=current_user.id,
        completed_only=completed_only,
        limit=limit
    )
    return completions


@router.get("/user/stats", response_model=TaskStatsResponse)
async def get_user_task_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's task completion statistics."""
    stats = await TaskService.get_user_task_stats(db, current_user.id)
    return stats


@router.post("/{task_id}/progress")
async def update_task_progress(
    task_id: int,
    progress_increment: int = Query(1, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update progress on a task (typically called by backend systems)."""
    try:
        completion = await TaskService.update_task_progress(
            db=db,
            user_id=current_user.id,
            task_id=task_id,
            progress_increment=progress_increment
        )
        return {
            "completion_id": completion.id,
            "current_progress": completion.current_progress,
            "required_progress": completion.required_progress,
            "is_completed": completion.is_completed,
            "vit_earned": float(completion.total_vit_earned),
            "xp_earned": completion.total_xp_earned
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Admin endpoints ────────────────────────────────────────────────────────────

@router.post("/categories", response_model=TaskCategoryResponse)
async def create_task_category(
    request: CreateTaskCategoryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new task category (admin only)."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    category = await TaskService.create_category(
        db=db,
        name=request.name,
        description=request.description,
        icon=request.icon,
        color=request.color,
        sort_order=request.sort_order
    )
    return category


@router.post("", response_model=TaskResponse)
async def create_task(
    request: CreateTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new task (admin only)."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Validate category exists
    category = await TaskService.get_category_by_id(db, request.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Task category not found")

    task = await TaskService.create_task(
        db=db,
        category_id=request.category_id,
        title=request.title,
        description=request.description,
        task_type=request.task_type,
        vit_reward=Decimal(str(request.vit_reward)),
        xp_reward=request.xp_reward,
        created_by=current_user.id,
        short_description=request.short_description,
        required_count=request.required_count,
        max_completions=request.max_completions,
        expires_at=request.expires_at,
        icon=request.icon,
        color=request.color,
        is_featured=request.is_featured,
        requirements=request.requirements
    )
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    request: UpdateTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a task (admin only)."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if updates:
        task = await TaskService.update_task(db, task_id, updates)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    # If no updates, return current task
    task = await TaskService.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a task (admin only)."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import delete
    result = await db.execute(delete(Task).where(Task.id == task_id))
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"success": True}


@router.post("/reset-expired")
async def reset_expired_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reset expired task progress (admin only)."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    reset_count = await TaskService.reset_expired_tasks(db)
    return {"reset_count": reset_count}