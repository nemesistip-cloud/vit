import logging
import asyncio
import time
from typing import Callable, Any, Optional, Dict

logger = logging.getLogger(__name__)

class RecoveryManager:
    """Manages failure recovery and retry policies for VIT modules (Native Implementation)."""

    def __init__(self, max_retries: int = 3, initial_wait: float = 1.0, max_wait: float = 10.0):
        self.max_retries = max_retries
        self.initial_wait = initial_wait
        self.max_wait = max_wait
        self.recovery_stats: Dict[str, int] = {}

    async def execute_with_recovery(self, module_id: str, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with manual exponential backoff retry logic."""

        last_exception = None
        wait_time = self.initial_wait

        for attempt in range(1, self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"[recovery] Attempt {attempt}/{self.max_retries} failed for {module_id}: {e}. "
                    f"Retrying in {wait_time:.2f}s..."
                )

                if attempt < self.max_retries:
                    await asyncio.sleep(wait_time)
                    wait_time = min(wait_time * 2, self.max_wait)

                self.recovery_stats[module_id] = self.recovery_stats.get(module_id, 0) + 1

        logger.error(f"[recovery] All {self.max_retries} attempts failed for {module_id}: {last_exception}")
        raise last_exception

    def get_stats(self) -> Dict[str, int]:
        return self.recovery_stats.copy()

    def reset_stats(self, module_id: str):
        if module_id in self.recovery_stats:
            self.recovery_stats[module_id] = 0
