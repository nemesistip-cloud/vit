from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.core.resource_platform.models import (
    Task, TaskPriority, LockInfo, ResourceQuota,
    WorkerInfo, RateLimitInfo
)

class IResourceManager(ABC):
    @abstractmethod
    async def allocate(self, task_id: str, quota: ResourceQuota) -> bool:
        pass

    @abstractmethod
    async def release(self, task_id: str):
        pass

    @abstractmethod
    async def get_utilization(self) -> Dict[str, Any]:
        pass

class IScheduler(ABC):
    @abstractmethod
    async def schedule_cron(self, name: str, cron: str, payload: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    async def schedule_delayed(self, name: str, delay_seconds: int, payload: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    async def cancel_schedule(self, schedule_id: str) -> bool:
        pass

class ITaskQueue(ABC):
    @abstractmethod
    async def enqueue(self, task: Task) -> bool:
        pass

    @abstractmethod
    async def dequeue(self, worker_id: str) -> Optional[Task]:
        pass

    @abstractmethod
    async def complete(self, task_id: str, result: Any = None):
        pass

    @abstractmethod
    async def fail(self, task_id: str, error: str, retry: bool = True):
        pass

class IWorkerManager(ABC):
    @abstractmethod
    async def start_workers(self, count: int):
        pass

    @abstractmethod
    async def stop_workers(self):
        pass

    @abstractmethod
    async def get_worker_stats(self) -> List[WorkerInfo]:
        pass

class IDistributedLockManager(ABC):
    @abstractmethod
    async def acquire(self, lock_id: str, owner: str, ttl_seconds: int = 60) -> bool:
        pass

    @abstractmethod
    async def release(self, lock_id: str, owner: str) -> bool:
        pass

    @abstractmethod
    async def extend(self, lock_id: str, owner: str, ttl_seconds: int = 60) -> bool:
        pass

class IRateLimiter(ABC):
    @abstractmethod
    async def check_limit(self, key: str, limit: int, window_seconds: int) -> bool:
        pass

    @abstractmethod
    async def get_limit_info(self, key: str) -> RateLimitInfo:
        pass
