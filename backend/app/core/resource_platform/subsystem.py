import logging
from typing import Dict, Any
from app.core.kernel import Subsystem
from app.core.resource_platform.resources import ResourceManager
from app.core.resource_platform.queue import TaskQueue
from app.core.resource_platform.workers import WorkerManager
from app.core.resource_platform.scheduler import Scheduler
from app.core.resource_platform.locks import DistributedLockManager
from app.core.resource_platform.limiter import RateLimiter
from app.core.observability.manager import obs_manager
from app.core.observability.models import HealthStatus

logger = logging.getLogger(__name__)

class ResourcePlatformSubsystem(Subsystem):
    """Authoritative execution engine for the VIT Ecosystem."""

    name = "resource_platform"
    dependencies = ["config", "observability", "redis"]

    def __init__(self, kernel):
        super().__init__(kernel)
        self.resource_manager = None
        self.queue = None
        self.worker_manager = None
        self.scheduler = None
        self.lock_manager = None
        self.rate_limiter = None
        self._disabled_reason = None

    async def _on_initialize(self, config: Dict[str, Any]):
        # Redis connects in RedisSubsystem._on_start, after all modules initialize.
        # Keep this optional subsystem from opening duplicate startup connections.
        logger.info("[kernel] Resource Platform initialization deferred until Redis is available.")

    async def _on_start(self):
        from app.core.redis import redis_client

        if redis_client is None:
            self._disabled_reason = "Redis unavailable"
            obs_manager.health.update_status(
                self.name,
                HealthStatus.DEGRADED,
                "Redis unavailable; queued task execution is disabled",
            )
            logger.warning("[kernel] Resource Platform disabled for this process: Redis unavailable.")
            return

        self.resource_manager = ResourceManager()
        self.queue = TaskQueue(redis_client)
        self.worker_manager = WorkerManager(self.queue, self.resource_manager)
        self.scheduler = Scheduler(self.queue, redis_client)
        self.lock_manager = DistributedLockManager(redis_client)
        self.rate_limiter = RateLimiter(redis_client)

        # Start workers
        worker_count = 2 # Default for small systems
        await self.worker_manager.start_workers(worker_count)

        # Start scheduler
        await self.scheduler.start()

        obs_manager.health.update_status(self.name, HealthStatus.HEALTHY, "Execution engine online")
        logger.info("[kernel] Resource Platform execution engine started.")

    async def _on_stop(self):
        if self.scheduler:
            await self.scheduler.stop()
        if self.worker_manager:
            await self.worker_manager.stop_workers()
        logger.info("[kernel] Resource Platform execution engine stopped.")

    async def health_check(self) -> bool:
        # Check if we can reach Redis
        try:
            if self.lock_manager is None:
                return False
            await self.lock_manager.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Resource Platform health check failed: {e}")
            return False

    async def get_diagnostics(self) -> Dict[str, Any]:
        stats = await self.resource_manager.get_utilization() if self.resource_manager else {}
        workers = await self.worker_manager.get_worker_stats() if self.worker_manager else []
        return {
            "resource_utilization": stats,
            "worker_count": len(workers),
            "workers": [w.dict() for w in workers]
        }
