import asyncio
import logging
from typing import List, Callable, Tuple, Dict, Any

logger = logging.getLogger(__name__)

class BackgroundTaskSupervisor:
    """
    Supervisor to monitor and restart critical background tasks.
    """
    def __init__(self, tasks: List[Tuple[str, Callable]], check_interval: float = 10.0, max_restarts: int = 5):
        self.tasks = tasks
        self.check_interval = check_interval
        self.max_restarts = max_restarts
        self.task_states = {name: {"restarts": 0, "running": False, "done": False, "error": None} for name, _ in tasks}
        self._running_tasks = {}
        self._shutdown_event = asyncio.Event()

    async def _run_task(self, name: str, coro_func: Callable):
        try:
            self.task_states[name]["running"] = True
            await coro_func()
            self.task_states[name]["done"] = True
        except Exception as e:
            logger.error(f"Background task {name} failed: {e}")
            self.task_states[name]["error"] = str(e)
        finally:
            self.task_states[name]["running"] = False

    async def _monitor(self):
        while not self._shutdown_event.is_set():
            for name, coro_func in self.tasks:
                state = self.task_states[name]
                if not state["running"] and not state["done"]:
                    if state["restarts"] < self.max_restarts:
                        state["restarts"] += 1
                        logger.info(f"Starting/Restarting task {name} (attempt {state['restarts']})")
                        task = asyncio.create_task(self._run_task(name, coro_func))
                        self._running_tasks[name] = task

            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=self.check_interval)
            except asyncio.TimeoutError:
                pass

    def start(self):
        self._monitor_task = asyncio.create_task(self._monitor())

    async def stop(self):
        self._shutdown_event.set()
        for name, task in self._running_tasks.items():
            if not task.done():
                task.cancel()
        await self._monitor_task

    def snapshot(self) -> Dict[str, Any]:
        return self.task_states
