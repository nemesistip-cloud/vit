"""Task system service layer — handles task creation, completion, and rewards."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.tasks.models import Task, TaskCategory, UserTaskCompletion, TaskType, TaskStatus
from app.db.models import User
from app.modules.wallet.services import WalletService
from app.core.dependencies import get_orchestrator

logger = logging.getLogger(__name__)


class TaskService:
    """Service for managing tasks, completions, and rewards."""

    @staticmethod
    async def get_categories(db: AsyncSession) -> List[TaskCategory]:
        """Get all active task categories."""
        result = await db.execute(
            select(TaskCategory).where(TaskCategory.is_active == True)
            .order_by(TaskCategory.sort_order, TaskCategory.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_category_by_id(db: AsyncSession, category_id: int) -> Optional[TaskCategory]:
        """Get a task category by ID."""
        result = await db.execute(
            select(TaskCategory).where(TaskCategory.id == category_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_category(
        db: AsyncSession,
        name: str,
        description: str = None,
        icon: str = None,
        color: str = None,
        sort_order: int = 0
    ) -> TaskCategory:
        """Create a new task category."""
        category = TaskCategory(
            name=name,
            description=description,
            icon=icon,
            color=color,
            sort_order=sort_order
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def get_tasks(
        db: AsyncSession,
        category_id: Optional[int] = None,
        status: Optional[str] = None,
        featured_only: bool = False,
        limit: int = 50
    ) -> List[Task]:
        """Get tasks with optional filtering."""
        query = select(Task).options(selectinload(Task.category), selectinload(Task.creator))

        if category_id:
            query = query.where(Task.category_id == category_id)

        if status:
            query = query.where(Task.status == status)
        else:
            query = query.where(Task.status == TaskStatus.ACTIVE.value)

        if featured_only:
            query = query.where(Task.is_featured == True)

        # Filter out expired tasks
        now = datetime.utcnow()
        query = query.where(or_(Task.expires_at.is_(None), Task.expires_at > now))

        query = query.order_by(Task.sort_order, Task.created_at.desc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_suggested_tasks(
        db: AsyncSession,
        user_id: int,
        limit: int = 10
    ) -> List[Task]:
        """Get the most relevant suggested tasks for a user."""
        tasks = await TaskService.get_tasks(db, limit=200)
        completions = await TaskService.get_user_task_completions(db, user_id=user_id, limit=500)
        completion_map = {completion.task_id: completion for completion in completions}

        suggestions = []
        for task in tasks:
            completion = completion_map.get(task.id)
            if completion and completion.is_completed:
                continue
            suggestions.append((task, completion))

        suggestions.sort(key=lambda entry: (
            0 if entry[0].is_featured else 1,
            0 if entry[1] and entry[1].current_progress > 0 else 1,
            -(float(entry[0].vit_reward or 0)),
            entry[0].task_type
        ))

        return [task for task, _ in suggestions[:limit]]

    @staticmethod
    async def get_task_by_id(db: AsyncSession, task_id: int) -> Optional[Task]:
        """Get a task by ID with category and creator loaded."""
        result = await db.execute(
            select(Task)
            .options(selectinload(Task.category), selectinload(Task.creator))
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_task(
        db: AsyncSession,
        category_id: int,
        title: str,
        description: str,
        task_type: str,
        created_by: int,
        vit_reward: Decimal = Decimal("0"),
        xp_reward: int = 0,
        **kwargs
    ) -> Task:
        """Create a new task."""
        task = Task(
            category_id=category_id,
            title=title,
            description=description,
            task_type=task_type,
            vit_reward=vit_reward,
            xp_reward=xp_reward,
            created_by=created_by,
            **kwargs
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def update_task(
        db: AsyncSession,
        task_id: int,
        updates: Dict[str, Any]
    ) -> Optional[Task]:
        """Update a task."""
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None

        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)

        task.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def get_user_task_completion(
        db: AsyncSession,
        user_id: int,
        task_id: int
    ) -> Optional[UserTaskCompletion]:
        """Get user's completion status for a specific task."""
        result = await db.execute(
            select(UserTaskCompletion)
            .where(
                and_(
                    UserTaskCompletion.user_id == user_id,
                    UserTaskCompletion.task_id == task_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_task_completions(
        db: AsyncSession,
        user_id: int,
        completed_only: bool = False,
        limit: int = 100
    ) -> List[UserTaskCompletion]:
        """Get all task completions for a user."""
        query = (
            select(UserTaskCompletion)
            .options(selectinload(UserTaskCompletion.task).selectinload(Task.category))
            .where(UserTaskCompletion.user_id == user_id)
        )

        if completed_only:
            query = query.where(UserTaskCompletion.is_completed == True)

        query = query.order_by(UserTaskCompletion.updated_at.desc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_task_progress(
        db: AsyncSession,
        user_id: int,
        task_id: int,
        progress_increment: int = 1
    ) -> UserTaskCompletion:
        """Update user progress on a task and check for completion."""
        # Get or create completion record
        completion = await TaskService.get_user_task_completion(db, user_id, task_id)
        if not completion:
            task = await TaskService.get_task_by_id(db, task_id)
            if not task:
                raise ValueError("Task not found")

            completion = UserTaskCompletion(
                user_id=user_id,
                task_id=task_id,
                required_progress=task.required_count
            )
            db.add(completion)

        # Update progress
        completion.current_progress += progress_increment
        completion.updated_at = datetime.utcnow()

        # Check if completed
        if (completion.current_progress >= completion.required_progress and
            not completion.is_completed):
            await TaskService._complete_task(db, completion)

        await db.commit()
        await db.refresh(completion)
        return completion

    @staticmethod
    def _resolve_reward_multiplier(task: Task, completion: UserTaskCompletion) -> Decimal:
        multiplier = Decimal(str(task.requirements.get("reward_multiplier", 1.0)))
        streak_bonus = Decimal(str(task.requirements.get("streak_bonus", 0)))

        if streak_bonus > 0 and task.task_type == TaskType.DAILY.value:
            streak_level = min(completion.completed_count, 5)
            multiplier += streak_bonus * Decimal(str(streak_level))

        return max(Decimal("1.0"), multiplier)

    @staticmethod
    async def _complete_task(
        db: AsyncSession,
        completion: UserTaskCompletion
    ) -> None:
        """Mark a task as completed and award rewards."""
        task = await TaskService.get_task_by_id(db, completion.task_id)
        if not task:
            return

        reward_multiplier = TaskService._resolve_reward_multiplier(task, completion)
        earned_vit = (task.vit_reward * reward_multiplier).quantize(Decimal("0.00000001"))

        # Mark as completed
        completion.is_completed = True
        completion.completed_count += 1
        completion.last_completed_at = datetime.utcnow()
        completion.total_vit_earned += earned_vit
        completion.total_xp_earned += task.xp_reward

        # Award VIT reward if any
        if earned_vit > 0:
            try:
                wallet_service = WalletService(db)
                await wallet_service.deposit_vitcoin(
                    user_id=completion.user_id,
                    amount=earned_vit,
                    description=f"Task completion: {task.title}",
                    tx_type="TASK_REWARD",
                    metadata={
                        "task_id": task.id,
                        "base_vit_reward": str(task.vit_reward),
                        "reward_multiplier": str(reward_multiplier),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to award VIT reward for task {task.id}: {e}")

        # Award XP
        if task.xp_reward > 0:
            result = await db.execute(
                select(User).where(User.id == completion.user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.total_xp += task.xp_reward
                user.updated_at = datetime.utcnow()

                # Check for XP-based task completion
                await TaskService.check_xp_based_tasks(db, completion.user_id)

        # Set next reset time for recurring tasks
        if task.task_type in [TaskType.DAILY.value, TaskType.WEEKLY.value, TaskType.MONTHLY.value]:
            now = datetime.utcnow()
            if task.task_type == TaskType.DAILY.value:
                completion.next_reset_at = now + timedelta(days=1)
            elif task.task_type == TaskType.WEEKLY.value:
                completion.next_reset_at = now + timedelta(weeks=1)
            elif task.task_type == TaskType.MONTHLY.value:
                # Approximate month as 30 days
                completion.next_reset_at = now + timedelta(days=30)

            # Reset progress for recurring tasks
            completion.current_progress = 0
            completion.is_completed = False

        logger.info(
            f"Task {task.id} completed by user {completion.user_id} "
            f"earned_vit={earned_vit} multiplier={reward_multiplier}"
        )

    @staticmethod
    async def reset_expired_tasks(db: AsyncSession) -> int:
        """Reset progress for tasks that have reached their reset time."""
        now = datetime.utcnow()
        result = await db.execute(
            select(UserTaskCompletion)
            .where(
                and_(
                    UserTaskCompletion.next_reset_at.is_not(None),
                    UserTaskCompletion.next_reset_at <= now,
                    UserTaskCompletion.is_completed == True
                )
            )
        )
        completions = list(result.scalars().all())

        reset_count = 0
        for completion in completions:
            completion.current_progress = 0
            completion.is_completed = False
            completion.next_reset_at = None  # Will be set on next completion
            reset_count += 1

        if reset_count > 0:
            await db.commit()
            logger.info(f"Reset {reset_count} expired task completions")

        return reset_count

    @staticmethod
    async def check_xp_based_tasks(db: AsyncSession, user_id: int) -> None:
        """Check and complete XP-based tasks automatically."""
        # Get user's current XP
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return

        current_xp = user.total_xp

        # Check Century Club (100 XP)
        if current_xp >= 100:
            try:
                await TaskService.update_task_progress(
                    db, user_id, 13, 100  # Task ID 13: "Century Club"
                )
            except Exception as e:
                logger.warning(f"XP task update failed for user {user_id}: {e}")

        # Check VIT Millionaire (1000 VIT earned total)
        # This would need to be checked when VIT is earned, not just XP
        # For now, we'll check it here as well
        vit_stats = await TaskService.get_user_task_stats(db, user_id)
        if vit_stats["total_vit_earned"] >= 1000:
            try:
                await TaskService.update_task_progress(
                    db, user_id, 14, 1000  # Task ID 14: "VIT Millionaire"
                )
            except Exception as e:
                logger.warning(f"VIT task update failed for user {user_id}: {e}")

    @staticmethod
    async def get_user_task_stats(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """Get task completion statistics for a user."""
        result = await db.execute(
            select(
                func.count(UserTaskCompletion.id).label("total_tasks"),
                func.sum(UserTaskCompletion.completed_count).label("total_completions"),
                func.sum(UserTaskCompletion.total_vit_earned).label("total_vit_earned"),
                func.sum(UserTaskCompletion.total_xp_earned).label("total_xp_earned")
            )
            .where(UserTaskCompletion.user_id == user_id)
        )
        row = result.first()

        return {
            "total_tasks_attempted": row.total_tasks or 0,
            "total_completions": row.total_completions or 0,
            "total_vit_earned": float(row.total_vit_earned or 0),
            "total_xp_earned": row.total_xp_earned or 0,
        }