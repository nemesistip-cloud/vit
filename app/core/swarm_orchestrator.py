"""
app/core/swarm_orchestrator.py

SwarmOrchestrator — v7.1 agent lifecycle manager with in-process APScheduler.
==============================================================================
Owns all autonomous agents, supervises their asyncio tasks, and exposes a
coordinator-compatible status/trigger interface.

APScheduler replaces the Celery Beat dependency (which cannot run on Render
free plans).  Every agent that exposes ``interval_seconds`` is scheduled with
AsyncIOScheduler automatically when ``start_scheduler()`` is called during
the FastAPI lifespan.

The single global instance is created at startup (main.py lifespan) via
``init_swarm(agents, tasks)`` and retrieved anywhere via ``get_swarm()``.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_SWARM: Optional["SwarmOrchestrator"] = None


def get_swarm() -> "SwarmOrchestrator":
    """Return the running SwarmOrchestrator or raise RuntimeError."""
    if _SWARM is None:
        raise RuntimeError("SwarmOrchestrator has not been initialised yet")
    return _SWARM


def set_swarm(swarm: "SwarmOrchestrator") -> None:
    """Register the global swarm instance (called once at startup)."""
    global _SWARM
    _SWARM = swarm
    logger.info("[swarm] global SwarmOrchestrator registered (%d agents)", len(swarm._agents))


class SwarmOrchestrator:
    """
    Supervisor for all autonomous VIT agents.

    Scheduling
    ----------
    Call ``start_scheduler()`` once inside the FastAPI lifespan after agents
    are registered.  It creates an ``AsyncIOScheduler`` (APScheduler) and
    adds an interval job for every agent that exposes ``interval_seconds``
    (default: 300 s).  This replaces the broken Celery Beat path on Render
    free plans.

    Attributes
    ----------
    _agents     : dict mapping agent name → agent instance
    _tasks      : list of asyncio.Task objects (one per agent loop)
    _started    : datetime when the swarm was initialised
    _scheduler  : APScheduler AsyncIOScheduler instance (or None if not started)
    """

    def __init__(self) -> None:
        self._agents: Dict[str, Any] = {}
        self._tasks: List[asyncio.Task] = []
        self._started: datetime = datetime.now(timezone.utc)
        self._trigger_log: List[Dict[str, Any]] = []
        self._scheduler: Any = None  # APScheduler AsyncIOScheduler

    # ── Registration ────────────────────────────────────────────────────────

    def register(self, name: str, agent: Any) -> None:
        """Register an agent instance under the given name."""
        self._agents[name] = agent

    def register_tasks(self, tasks: List[asyncio.Task]) -> None:
        """Store the asyncio.Task list so status() can report running/stopped."""
        self._tasks = tasks

    # ── APScheduler in-process scheduling ───────────────────────────────────

    def start_scheduler(self) -> None:
        """
        Start the in-process APScheduler for all registered agents.

        Replaces Celery Beat.  Each agent gets an interval job based on its
        ``interval_seconds`` attribute (default 300 s = 5 min).  Errors in
        individual agent runs are caught and logged — they never crash the
        scheduler.
        """
        if not self._agents:
            logger.info("[swarm] No agents registered — skipping scheduler start.")
            return

        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
        except ImportError:
            logger.warning(
                "[swarm] APScheduler not installed — agents will not run automatically. "
                "Add 'apscheduler' to requirements.txt to enable background agents."
            )
            return

        self._scheduler = AsyncIOScheduler(timezone="UTC")

        scheduled = 0
        for name, agent in self._agents.items():
            interval = getattr(agent, "interval_seconds", 300)
            # Stagger start times by 5 s per agent to avoid thundering-herd on boot
            start_delay = 30 + (scheduled * 5)

            async def _agent_job(agent=agent, name=name) -> None:
                try:
                    await agent.run_once()
                    logger.debug("[swarm] agent '%s' cycle complete", name)
                except Exception as exc:
                    logger.warning("[swarm] agent '%s' error: %s", name, exc)

            self._scheduler.add_job(
                _agent_job,
                trigger="interval",
                seconds=max(int(interval), 30),  # Floor at 30 s
                id=f"agent_{name}",
                name=f"VIT Agent: {name}",
                replace_existing=True,
                misfire_grace_time=60,
                next_run_time=datetime.now(timezone.utc).replace(
                    second=0, microsecond=0
                ).__class__.fromtimestamp(
                    datetime.now(timezone.utc).timestamp() + start_delay,
                    tz=timezone.utc,
                ),
            )
            scheduled += 1
            logger.info(
                "[swarm] scheduled agent '%s' every %ds (first run in ~%ds)",
                name, interval, start_delay,
            )

        self._scheduler.start()
        logger.info(
            "[swarm] APScheduler started — %d agent(s) scheduled in-process", scheduled
        )

    def stop_scheduler(self) -> None:
        """Gracefully shut down the APScheduler (call from lifespan shutdown)."""
        if self._scheduler is not None:
            try:
                self._scheduler.shutdown(wait=False)
                logger.info("[swarm] APScheduler stopped.")
            except Exception as exc:
                logger.warning("[swarm] APScheduler shutdown error: %s", exc)

    # ── Status / trigger (AgentCoordinator-compatible) ──────────────────────

    def status(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of all agents."""
        running = sum(1 for t in self._tasks if not t.done())
        stopped = len(self._tasks) - running

        sched_jobs: Dict[str, Any] = {}
        if self._scheduler is not None:
            for job in self._scheduler.get_jobs():
                sched_jobs[job.id] = {
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "interval_seconds": job.trigger.interval.total_seconds()
                    if hasattr(job.trigger, "interval")
                    else None,
                }

        agents_status = {}
        for name, agent in self._agents.items():
            agents_status[name] = {
                "name": name,
                "running": True,
                "last_run": getattr(agent, "last_run", None),
                "run_count": getattr(agent, "run_count", 0),
                "last_error": getattr(agent, "last_error", None),
                "interval_seconds": getattr(agent, "interval_seconds", 300),
                "scheduler": sched_jobs.get(f"agent_{name}"),
            }

        return {
            "total_agents": len(self._agents),
            "running_tasks": running,
            "stopped_tasks": stopped,
            "scheduler_active": self._scheduler is not None and self._scheduler.running,
            "started_at": self._started.isoformat(),
            "agents": agents_status,
        }

    def trigger(self, name: str) -> Dict[str, Any]:
        """Manually trigger an agent cycle (non-blocking fire-and-forget)."""
        agent = self._agents.get(name)
        if agent is None:
            return {"ok": False, "error": f"Agent '{name}' not found"}

        async def _run() -> None:
            try:
                await agent.run_once()
            except Exception as exc:
                logger.warning("[swarm] manual trigger error for %s: %s", name, exc)

        asyncio.create_task(_run())
        event = {
            "agent": name,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "source": "manual",
        }
        self._trigger_log.append(event)
        return {"ok": True, "agent": name}

    # ── dict-like helpers for legacy coordinator code ────────────────────────

    def get(self, name: str, default: Any = None) -> Any:
        return self._agents.get(name, default)

    def __contains__(self, name: str) -> bool:
        return name in self._agents

    def __len__(self) -> int:
        return len(self._agents)
