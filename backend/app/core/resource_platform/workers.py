import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from app.core.resource_platform.contract import IWorkerManager, ITaskQueue, IResourceManager
from app.core.resource_platform.models import WorkerInfo, WorkerStatus, TaskStatus
from app.core.resource_platform.context import ExecutionContext
from app.core.observability.manager import obs_manager

logger = logging.getLogger(__name__)

class Worker:
    def __init__(self, worker_id: str, queue: ITaskQueue, resource_manager: IResourceManager):
        self.worker_id = worker_id
        self.queue = queue
        self.resource_manager = resource_manager
        self.status = WorkerStatus.IDLE
        self.current_task_id: Optional[str] = None
        self.tasks_processed = 0
        self.start_time = time.time()
        self._shutdown_event = asyncio.Event()

    async def run(self):
        self.status = WorkerStatus.IDLE
        while not self._shutdown_event.is_set():
            try:
                task = await self.queue.dequeue(self.worker_id)
                if not task:
                    await asyncio.sleep(1)
                    continue

                self.status = WorkerStatus.BUSY
                self.current_task_id = task.id

                # Allocate resources
                if await self.resource_manager.allocate(task.id, task.quota):
                    try:
                        ctx = ExecutionContext(task_id=task.id, timeout=task.quota.timeout_seconds)
                        # Execute task (Mock execution logic here, usually would call a registry)
                        logger.info(f"Worker {self.worker_id} executing task {task.name} ({task.id})")
                        # In real impl: await self.registry.execute(task.name, task.payload, ctx)
                        await asyncio.sleep(0.1) # Simulate work

                        await self.queue.complete(task.id)
                        latency = (asyncio.get_event_loop().time() - task.started_at) * 1000
                        obs_manager.record_metric("resource_platform.task_latency", latency)
                    except Exception as e:
                        logger.error(f"Task {task.id} failed on worker {self.worker_id}: {e}")
                        await self.queue.fail(task.id, str(e))
                    finally:
                        await self.resource_manager.release(task.id)
                else:
                    await self.queue.fail(task.id, "Resource allocation failed", retry=True)

                self.tasks_processed += 1
                self.current_task_id = None
                self.status = WorkerStatus.IDLE

            except Exception as e:
                logger.error(f"Worker {self.worker_id} loop error: {e}")
                await asyncio.sleep(5)

        self.status = WorkerStatus.STOPPED

    def stop(self):
        self._shutdown_event.set()

class WorkerManager(IWorkerManager):
    def __init__(self, queue: ITaskQueue, resource_manager: IResourceManager):
        self.queue = queue
        self.resource_manager = resource_manager
        self.workers: List[Worker] = []
        self.worker_tasks: List[asyncio.Task] = []

    async def start_workers(self, count: int):
        logger.info(f"Starting {count} workers...")
        for i in range(count):
            worker = Worker(f"worker-{i}", self.queue, self.resource_manager)
            self.workers.append(worker)
            self.worker_tasks.append(asyncio.create_task(worker.run()))

        obs_manager.record_metric("resource_platform.active_workers", len(self.workers))

    async def stop_workers(self):
        logger.info("Stopping all workers...")
        for worker in self.workers:
            worker.stop()

        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)

        self.workers = []
        self.worker_tasks = []
        obs_manager.record_metric("resource_platform.active_workers", 0)

    async def get_worker_stats(self) -> List[WorkerInfo]:
        return [
            WorkerInfo(
                worker_id=w.worker_id,
                status=w.status,
                current_task_id=w.current_task_id,
                tasks_processed=w.tasks_processed,
                uptime_seconds=time.time() - w.start_time,
                resource_usage={}
            ) for w in self.workers
        ]

# Additional metrics for worker performance
def record_task_latency(task_name: str, latency_ms: float):
    obs_manager.record_metric(f"resource_platform.task_latency.{task_name}", latency_ms)
