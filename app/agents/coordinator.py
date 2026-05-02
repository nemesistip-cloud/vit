"""app/agents/coordinator.py

AgentCoordinator — singleton that owns all agents and exposes a unified
status view to the API layer.

Usage (in main.py lifespan):
    from app.agents.coordinator import AgentCoordinator, get_coordinator
    coordinator = AgentCoordinator()
    coordinator.register_tasks(tasks_list)   # add asyncio tasks for each agent loop
    app.state.agent_coordinator = coordinator

API route reads:
    coordinator = get_coordinator()
    coordinator.status()         # full JSON snapshot
    coordinator.trigger(name)    # manual agent trigger
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_GLOBAL_COORDINATOR: Optional["AgentCoordinator"] = None


def get_coordinator() -> "AgentCoordinator":
    global _GLOBAL_COORDINATOR
    if _GLOBAL_COORDINATOR is None:
        _GLOBAL_COORDINATOR = AgentCoordinator()
    return _GLOBAL_COORDINATOR


class AgentCoordinator:
    """Central registry and controller for all autonomous agents."""

    def __init__(self) -> None:
        global _GLOBAL_COORDINATOR
        _GLOBAL_COORDINATOR = self

        from app.agents.performance_monitor import PerformanceMonitorAgent
        from app.agents.weight_optimizer    import WeightOptimizerAgent
        from app.agents.retrain_trigger     import RetrainTriggerAgent
        from app.agents.match_scout_agent   import MatchScoutAgent
        from app.agents.news_sentinel_agent import NewsSentinelAgent
        from app.agents.odds_anomaly_agent  import OddsAnomalyAgent

        self._agents = {
            # ── ML performance agents ────────────────────────────────────
            "performance-monitor": PerformanceMonitorAgent(),
            "weight-optimizer":    WeightOptimizerAgent(),
            "retrain-trigger":     RetrainTriggerAgent(),
            # ── AI-powered intelligence agents (free keys) ───────────────
            "match-scout":         MatchScoutAgent(),
            "news-sentinel":       NewsSentinelAgent(),
            "odds-anomaly":        OddsAnomalyAgent(),
        }
        self._tasks: List[asyncio.Task] = []
        self._started_at = datetime.now(timezone.utc)

        logger.info("[coordinator] initialised with %d agents", len(self._agents))

    def start(self, task_list: Optional[List[asyncio.Task]] = None) -> List[asyncio.Task]:
        """Launch all agent loops as asyncio tasks.

        Returns the created tasks so they can be tracked by the caller
        (e.g. added to the main.py tasks list for clean shutdown).
        """
        for name, agent in self._agents.items():
            task = asyncio.create_task(agent.loop(), name=f"agent-{name}")
            self._tasks.append(task)
            if task_list is not None:
                task_list.append(task)
            logger.info("[coordinator] agent task created: %s", name)
        return self._tasks

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("[coordinator] all agent tasks stopped")

    # ── Public API ─────────────────────────────────────────────────────────

    def trigger(self, agent_name: str) -> bool:
        """Manually trigger an agent's next cycle immediately."""
        agent = self._agents.get(agent_name)
        if agent is None:
            return False
        agent.trigger()
        return True

    def get_agent_result(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Return the last_result of an agent, or None."""
        agent = self._agents.get(agent_name)
        return agent.last_result if agent else None

    def status(self) -> Dict[str, Any]:
        """Return a full status snapshot of all agents."""
        return {
            "coordinator": {
                "started_at":    self._started_at.isoformat(),
                "agent_count":   len(self._agents),
                "running_tasks": sum(1 for t in self._tasks if not t.done()),
            },
            "agents": {name: agent.snapshot() for name, agent in self._agents.items()},
        }

    def summary(self) -> Dict[str, Any]:
        """Lightweight summary: one row per agent with key health fields."""
        rows = []
        for name, agent in self._agents.items():
            rows.append({
                "name":        name,
                "status":      agent.status,
                "run_count":   agent.run_count,
                "error_count": agent.error_count,
                "last_run_at": agent.last_run_at.isoformat() if agent.last_run_at else None,
                "next_run_at": agent.next_run_at.isoformat() if agent.next_run_at else None,
                "last_error":  agent.last_error,
            })
        return {
            "started_at": self._started_at.isoformat(),
            "agents":     rows,
        }
