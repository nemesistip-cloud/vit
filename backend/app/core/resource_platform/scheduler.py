import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.core.resource_platform.contract import IScheduler, ITaskQueue
from app.core.resource_platform.models import Task, TaskPriority
from app.core.observability.manager import obs_manager

logger = logging.getLogger(__name__)

class Scheduler(IScheduler):
    def __init__(self, queue: ITaskQueue, redis_client):
        self.queue = queue
        self.redis = redis_client
        self.prefix = "vit:scheduler:schedules:"
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None

    async def schedule_cron(self, name: str, cron: str, payload: Dict[str, Any]) -> str:
        schedule_id = f"cron:{name}:{uuid.uuid4().hex[:8]}"
        data = {
            "id": schedule_id,
            "name": name,
            "cron": cron,
            "payload": payload,
            "type": "CRON",
            "last_run": None
        }
        await self.redis.hset(self.prefix, schedule_id, json.dumps(data))
        obs_manager.record_metric("resource_platform.schedule_created", 1)
        return schedule_id

    async def schedule_delayed(self, name: str, delay_seconds: int, payload: Dict[str, Any]) -> str:
        schedule_id = f"delayed:{name}:{uuid.uuid4().hex[:8]}"
        run_at = (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat()
        data = {
            "id": schedule_id,
            "name": name,
            "run_at": run_at,
            "payload": payload,
            "type": "DELAYED"
        }
        await self.redis.hset(self.prefix, schedule_id, json.dumps(data))
        obs_manager.record_metric("resource_platform.schedule_created", 1)
        return schedule_id

    async def cancel_schedule(self, schedule_id: str) -> bool:
        result = await self.redis.hdel(self.prefix, schedule_id)
        if result:
            obs_manager.record_metric("resource_platform.schedule_cancelled", 1)
        return bool(result)

    async def start(self):
        if self._running:
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler engine started.")

    async def stop(self):
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler engine stopped.")

    async def _scheduler_loop(self):
        while self._running:
            try:
                schedules = await self.redis.hgetall(self.prefix)
                now = datetime.utcnow()

                for sid, raw_data in schedules.items():
                    data = json.loads(raw_data)
                    should_run = False

                    if data["type"] == "DELAYED":
                        run_at = datetime.fromisoformat(data["run_at"])
                        if now >= run_at:
                            should_run = True
                    elif data["type"] == "CRON":
                        # Simple cron logic: run every minute if it hasn't run this minute
                        # In real impl: use croniter
                        last_run_str = data.get("last_run")
                        if not last_run_str or (now - datetime.fromisoformat(last_run_str)).total_seconds() >= 60:
                            should_run = True

                    if should_run:
                        task = Task(
                            name=data["name"],
                            payload=data["payload"],
                            priority=TaskPriority.MEDIUM,
                            correlation_id=sid
                        )
                        await self.queue.enqueue(task)

                        if data["type"] == "DELAYED":
                            await self.redis.hdel(self.prefix, sid)
                        else:
                            data["last_run"] = now.isoformat()
                            await self.redis.hset(self.prefix, sid, json.dumps(data))

                        obs_manager.record_metric("resource_platform.schedule_triggered", 1)

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")

            await asyncio.sleep(10) # Check every 10 seconds
