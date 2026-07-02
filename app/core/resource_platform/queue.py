import json
import logging
import asyncio
from typing import Optional, Any, Dict
from app.core.resource_platform.contract import ITaskQueue
from app.core.resource_platform.models import Task, TaskStatus, TaskPriority
from app.core.observability.manager import obs_manager

logger = logging.getLogger(__name__)

class TaskQueue(ITaskQueue):
    def __init__(self, redis_client):
        self.redis = redis_client
        self.queue_prefix = "vit:task:queue:"
        self.data_prefix = "vit:task:data:"

    def _get_queue_key(self, priority: TaskPriority) -> str:
        return f"{self.queue_prefix}{priority.name.lower()}"

    async def enqueue(self, task: Task) -> bool:
        task.status = TaskStatus.QUEUED
        queue_key = self._get_queue_key(task.priority)
        data_key = f"{self.data_prefix}{task.id}"

        # Store task data and push ID to priority queue
        pipeline = self.redis.pipeline()
        pipeline.set(data_key, task.json())
        pipeline.lpush(queue_key, task.id)
        await pipeline.execute()

        obs_manager.record_metric("resource_platform.task_enqueued", 1)
        return True

    async def dequeue(self, worker_id: str) -> Optional[Task]:
        # Try priority queues in order: CRITICAL -> HIGH -> MEDIUM -> LOW
        priorities = [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]

        for p in priorities:
            queue_key = self._get_queue_key(p)
            # RPOP from the right side of the list (FIFO)
            task_id = await self.redis.rpop(queue_key)
            if task_id:
                data_key = f"{self.data_prefix}{task_id}"
                raw_task = await self.redis.get(data_key)
                if raw_task:
                    task = Task.parse_raw(raw_task)
                    task.status = TaskStatus.RUNNING
                    task.started_at = asyncio.get_event_loop().time()
                    await self.redis.set(data_key, task.json())

                    obs_manager.record_metric("resource_platform.task_dequeued", 1)
                    return task

        return None

    async def complete(self, task_id: str, result: Any = None):
        data_key = f"{self.data_prefix}{task_id}"
        raw_task = await self.redis.get(data_key)
        if raw_task:
            task = Task.parse_raw(raw_task)
            task.status = TaskStatus.COMPLETED
            task.finished_at = asyncio.get_event_loop().time()
            # In a real impl, we might move to a 'completed' set or expire
            await self.redis.setex(data_key, 3600, task.json())
            obs_manager.record_metric("resource_platform.task_completed", 1)

    async def fail(self, task_id: str, error: str, retry: bool = True):
        data_key = f"{self.data_prefix}{task_id}"
        raw_task = await self.redis.get(data_key)
        if raw_task:
            task = Task.parse_raw(raw_task)
            task.error = error

            if retry and task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                await self.enqueue(task)
                obs_manager.record_metric("resource_platform.task_retried", 1)
            else:
                task.status = TaskStatus.FAILED
                task.finished_at = asyncio.get_event_loop().time()
                await self.redis.setex(data_key, 86400, task.json())
                obs_manager.record_metric("resource_platform.task_failed", 1)
