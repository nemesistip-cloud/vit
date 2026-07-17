import asyncio
import logging
import psutil
from typing import Dict, Any, Set
from app.core.resource_platform.contract import IResourceManager
from app.core.resource_platform.models import ResourceQuota
from app.core.observability.manager import obs_manager

logger = logging.getLogger(__name__)

class ResourceManager(IResourceManager):
    def __init__(self):
        self._allocated_tasks: Dict[str, ResourceQuota] = {}
        self._lock = asyncio.Lock()
        self._max_cpu_percent = 80.0
        self._max_memory_percent = 80.0

    async def allocate(self, task_id: str, quota: ResourceQuota) -> bool:
        async with self._lock:
            # Check current system pressure
            cpu_usage = psutil.cpu_percent()
            mem_usage = psutil.virtual_memory().percent

            if cpu_usage > self._max_cpu_percent or mem_usage > self._max_memory_percent:
                logger.warning(f"Resource allocation denied for {task_id}: System under pressure (CPU: {cpu_usage}%, MEM: {mem_usage}%)")
                return False

            self._allocated_tasks[task_id] = quota
            obs_manager.record_metric("resource_platform.allocated_tasks", len(self._allocated_tasks))
            return True

    async def release(self, task_id: str):
        async with self._lock:
            if task_id in self._allocated_tasks:
                del self._allocated_tasks[task_id]
                obs_manager.record_metric("resource_platform.allocated_tasks", len(self._allocated_tasks))

    async def get_utilization(self) -> Dict[str, Any]:
        return {
            "system_cpu_percent": psutil.cpu_percent(),
            "system_memory_percent": psutil.virtual_memory().percent,
            "allocated_tasks_count": len(self._allocated_tasks),
            "tracked_cpu_cores": sum(q.cpu_cores for q in self._allocated_tasks.values()),
            "tracked_memory_mb": sum(q.memory_mb for q in self._allocated_tasks.values())
        }
