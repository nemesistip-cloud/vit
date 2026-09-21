"""
TRACK-007: Agent Workflow Manager
Autonomous task execution and routing for VIT AI agents.

Provides:
- WorkflowDispatcher: routes tasks to registered agents
- WorkflowTask: represents a unit of work
- AgentWorkflowSubsystem: kernel integration
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class WorkflowTask:
    """A single unit of work routed to an agent."""

    def __init__(
        self,
        task_type: str,
        payload: Dict[str, Any],
        agent_id: Optional[str] = None,
        priority: int = 5,
        max_retries: int = 3,
        timeout_s: float = 30.0,
    ):
        self.task_id = str(uuid.uuid4())
        self.task_type = task_type
        self.payload = payload
        self.agent_id = agent_id
        self.priority = priority
        self.max_retries = max_retries
        self.timeout_s = timeout_s
        self.status = WorkflowStatus.PENDING
        self.retries = 0
        self.result: Optional[Dict] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "agent_id": self.agent_id,
            "priority": self.priority,
            "status": self.status.value,
            "retries": self.retries,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


class AgentHandler:
    """Registered handler for a specific task type."""

    def __init__(self, agent_id: str, task_type: str, handler: Callable):
        self.agent_id = agent_id
        self.task_type = task_type
        self.handler = handler
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_latency_ms = 0.0


class WorkflowDispatcher:
    """
    Central dispatcher that routes WorkflowTasks to registered AgentHandlers.

    Usage:
        dispatcher = WorkflowDispatcher()
        dispatcher.register("prediction", "vit-prediction-engine", my_handler)
        task = await dispatcher.submit("prediction", {"match_id": 42})
        await dispatcher.start()
    """

    def __init__(self, max_concurrency: int = 8, queue_size: int = 500):
        self._handlers: Dict[str, List[AgentHandler]] = {}
        self._tasks: Dict[str, WorkflowTask] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=queue_size)
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    def register(self, task_type: str, agent_id: str, handler: Callable) -> None:
        """Register a handler function for a task type."""
        h = AgentHandler(agent_id=agent_id, task_type=task_type, handler=handler)
        self._handlers.setdefault(task_type, []).append(h)
        logger.info("[workflow] registered handler agent=%s type=%s", agent_id, task_type)

    async def submit(
        self,
        task_type: str,
        payload: Dict[str, Any],
        agent_id: Optional[str] = None,
        priority: int = 5,
        max_retries: int = 3,
        timeout_s: float = 30.0,
    ) -> WorkflowTask:
        """Submit a task; returns immediately with the task object."""
        task = WorkflowTask(
            task_type=task_type,
            payload=payload,
            agent_id=agent_id,
            priority=priority,
            max_retries=max_retries,
            timeout_s=timeout_s,
        )
        self._tasks[task.task_id] = task
        # Lower number = higher priority in PriorityQueue
        await self._queue.put((10 - priority, task.created_at.timestamp(), task.task_id))
        logger.debug("[workflow] submitted task=%s type=%s", task.task_id, task_type)
        return task

    def get_task(self, task_id: str) -> Optional[WorkflowTask]:
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[WorkflowStatus] = None,
        task_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in tasks[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        all_tasks = list(self._tasks.values())
        by_status: Dict[str, int] = {}
        for t in all_tasks:
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1

        handler_stats = {}
        for task_type, handlers in self._handlers.items():
            handler_stats[task_type] = [
                {
                    "agent_id": h.agent_id,
                    "completed": h.tasks_completed,
                    "failed": h.tasks_failed,
                    "avg_latency_ms": round(h.total_latency_ms / max(h.tasks_completed, 1), 1),
                }
                for h in handlers
            ]

        return {
            "running": self._running,
            "queue_depth": self._queue.qsize(),
            "total_tasks": len(all_tasks),
            "by_status": by_status,
            "handlers": handler_stats,
        }

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._run_loop(), name="workflow-dispatcher")
        logger.info("[workflow] dispatcher started")

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("[workflow] dispatcher stopped")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                # Non-blocking get with timeout so we can check _running
                try:
                    _, _, task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                task = self._tasks.get(task_id)
                if not task or task.status == WorkflowStatus.CANCELLED:
                    self._queue.task_done()
                    continue

                asyncio.create_task(self._execute_task(task))
                self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("[workflow] dispatcher loop error: %s", e)

    async def _execute_task(self, task: WorkflowTask) -> None:
        handlers = self._handlers.get(task.task_type, [])
        if not handlers:
            task.status = WorkflowStatus.FAILED
            task.error = f"No handler registered for task type '{task.task_type}'"
            task.finished_at = datetime.now(timezone.utc)
            logger.warning("[workflow] no handler for type=%s", task.task_type)
            return

        # Select handler: prefer agent_id match, else round-robin
        handler = handlers[0]
        if task.agent_id:
            for h in handlers:
                if h.agent_id == task.agent_id:
                    handler = h
                    break

        async with self._semaphore:
            task.status = WorkflowStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)

            while task.retries <= task.max_retries:
                start_ms = asyncio.get_event_loop().time() * 1000
                try:
                    result = await asyncio.wait_for(
                        handler.handler(task.payload),
                        timeout=task.timeout_s,
                    )
                    task.result = result if isinstance(result, dict) else {"output": result}
                    task.status = WorkflowStatus.COMPLETED
                    task.finished_at = datetime.now(timezone.utc)
                    elapsed = asyncio.get_event_loop().time() * 1000 - start_ms
                    handler.tasks_completed += 1
                    handler.total_latency_ms += elapsed
                    logger.debug("[workflow] task=%s completed in %.1fms", task.task_id, elapsed)
                    return

                except asyncio.TimeoutError:
                    task.error = f"Handler timed out after {task.timeout_s}s"
                except Exception as e:
                    task.error = str(e)

                task.retries += 1
                if task.retries <= task.max_retries:
                    task.status = WorkflowStatus.RETRYING
                    logger.warning(
                        "[workflow] task=%s retry %d/%d: %s",
                        task.task_id, task.retries, task.max_retries, task.error,
                    )
                    await asyncio.sleep(2 ** task.retries)  # exponential backoff

            task.status = WorkflowStatus.FAILED
            task.finished_at = datetime.now(timezone.utc)
            handler.tasks_failed += 1
            logger.error("[workflow] task=%s failed after %d retries: %s", task.task_id, task.retries, task.error)


# ── Singleton dispatcher ───────────────────────────────────────────────────────
workflow_dispatcher = WorkflowDispatcher(max_concurrency=8)


def _register_builtin_handlers() -> None:
    """Register built-in VIT agent handlers."""

    async def _prediction_handler(payload: Dict) -> Dict:
        """Default prediction handler — delegates to AI orchestrator."""
        from app.core.dependencies import get_orchestrator
        orch = get_orchestrator()
        if not orch:
            return {"status": "skipped", "reason": "orchestrator unavailable"}
        match_id = payload.get("match_id")
        if match_id:
            return {"status": "dispatched", "match_id": match_id}
        return {"status": "no_op"}

    async def _sentinel_handler(payload: Dict) -> Dict:
        """Network guardian — checks subsystem health."""
        from app.core.kernel import kernel
        status = kernel.get_status()
        return {"status": "checked", "kernel_state": status.get("kernel_state")}

    async def _settlement_handler(payload: Dict) -> Dict:
        """Settlement agent — placeholder for on-chain settlement dispatch."""
        return {"status": "queued", "tx_ref": payload.get("tx_ref")}

    workflow_dispatcher.register("prediction", "vit-prediction-engine", _prediction_handler)
    workflow_dispatcher.register("health_check", "vit-network-guardian", _sentinel_handler)
    workflow_dispatcher.register("settlement", "vit-settlement-agent", _settlement_handler)


_register_builtin_handlers()
