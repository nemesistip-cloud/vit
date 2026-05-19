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
    """
    Return the active agent coordinator.

    Prefers the running SwarmOrchestrator (registered at startup via
    ``set_swarm()``) because it supervises all 22 agents. Falls back to the
    legacy AgentCoordinator singleton if the swarm is unavailable.
    """
    global _GLOBAL_COORDINATOR
    # ── Try SwarmOrchestrator first (v7.0 preferred path) ──────────────
    try:
        from app.core.swarm_orchestrator import get_swarm
        swarm = get_swarm()
        # Wrap SwarmOrchestrator so callers that use AgentCoordinator-style
        # attribute access (e.g. coordinator._agents) still work.
        return swarm  # type: ignore[return-value]
    except (RuntimeError, ModuleNotFoundError, ImportError):
        pass  # swarm not yet initialised or module missing — fall back below

    # ── Legacy AgentCoordinator fallback ───────────────────────────────
    if _GLOBAL_COORDINATOR is None:
        _GLOBAL_COORDINATOR = AgentCoordinator()
    return _GLOBAL_COORDINATOR


class AgentCoordinator:
    """Central registry and controller for all autonomous agents."""

    def __init__(self) -> None:
        from app.agents.performance_monitor          import PerformanceMonitorAgent
        from app.agents.weight_optimizer             import WeightOptimizerAgent
        from app.agents.retrain_trigger              import RetrainTriggerAgent
        from app.agents.match_scout_agent            import MatchScoutAgent
        from app.agents.news_sentinel_agent          import NewsSentinelAgent
        from app.agents.odds_anomaly_agent           import OddsAnomalyAgent
        # ── 14 autonomous agents ─────────────────────────────────────────
        from app.agents.kyc_screener_agent           import KYCScreenerAgent
        from app.agents.fraud_review_agent           import FraudReviewAgent
        from app.agents.withdrawal_gatekeeper_agent  import WithdrawalGatekeeperAgent
        from app.agents.marketplace_audit_agent      import MarketplaceAuditAgent
        from app.agents.model_promoter_agent         import ModelPromoterAgent
        from app.agents.analytics_reporter_agent     import AnalyticsReporterAgent
        from app.agents.fixture_gap_agent            import FixtureGapAgent
        from app.agents.accumulator_publisher_agent  import AccumulatorPublisherAgent
        from app.agents.revenue_optimizer_agent      import RevenueOptimizerAgent
        from app.agents.governance_executor_agent    import GovernanceExecutorAgent
        from app.agents.self_healing_agent           import SelfHealingAgent
        from app.agents.audit_sentinel_agent         import AuditSentinelAgent
        from app.agents.prediction_moderator_agent   import PredictionModeratorAgent
        from app.agents.live_match_tracker_agent     import LiveMatchTrackerAgent
        # ── VIT Oracle + Network agents ──────────────────────────────────
        from app.agents.oracle_node_agent            import OracleNodeAgent
        from app.agents.network_guardian_agent       import NetworkGuardianAgent

        self._agents = {
            # ── ML performance agents ────────────────────────────────────
            "performance-monitor":      PerformanceMonitorAgent(),
            "weight-optimizer":         WeightOptimizerAgent(),
            "retrain-trigger":          RetrainTriggerAgent(),
            # ── AI-powered intelligence agents (free keys) ───────────────
            "match-scout":              MatchScoutAgent(),
            "news-sentinel":            NewsSentinelAgent(),
            "odds-anomaly":             OddsAnomalyAgent(),
            # ── Autonomous human-replacement agents (items 1-14) ─────────
            "kyc-screener":             KYCScreenerAgent(),
            "fraud-review":             FraudReviewAgent(),
            "withdrawal-gatekeeper":    WithdrawalGatekeeperAgent(),
            "marketplace-audit":        MarketplaceAuditAgent(),
            "model-promoter":           ModelPromoterAgent(),
            "analytics-reporter":       AnalyticsReporterAgent(),
            "fixture-gap":              FixtureGapAgent(),
            "accumulator-publisher":    AccumulatorPublisherAgent(),
            "revenue-optimizer":        RevenueOptimizerAgent(),
            "governance-executor":      GovernanceExecutorAgent(),
            "self-healing":             SelfHealingAgent(),
            "audit-sentinel":           AuditSentinelAgent(),
            "prediction-moderator":     PredictionModeratorAgent(),
            # ── Real-time tracking ───────────────────────────────────────
            "live-match-tracker":       LiveMatchTrackerAgent(),
            # ── VIT Oracle Node ──────────────────────────────────────────
            "oracle-node":              OracleNodeAgent(),
            # ── VIT Network Guardian (DID + node registry) ───────────────
            # Rebranded to Value Intelligence Trust (VIT)
            "network-guardian":         NetworkGuardianAgent(),
        }
        self._tasks: List[asyncio.Task] = []
        self._started_at = datetime.now(timezone.utc)

        global _GLOBAL_COORDINATOR
        _GLOBAL_COORDINATOR = self
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
            logger.info("[coordinator] agent task created: %s (node_id=%s)", name, agent.node_id)
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
                "name":               name,
                "node_id":            agent.node_id,
                "status":             agent.status,
                "run_count":          agent.run_count,
                "error_count":        agent.error_count,
                "contribution_count": agent.contribution_count,
                "contribution_score": round(agent.contribution_score, 2),
                "last_run_at":        agent.last_run_at.isoformat() if agent.last_run_at else None,
                "next_run_at":        agent.next_run_at.isoformat() if agent.next_run_at else None,
                "last_error":         agent.last_error,
            })
        return {
            "started_at": self._started_at.isoformat(),
            "agents":     rows,
        }

    def network_summary(self) -> Dict[str, Any]:
        """Network-focused summary: node IDs, contribution scores, online status."""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        nodes = []
        for name, agent in self._agents.items():
            last_run = agent.last_run_at
            online = (
                last_run is not None
                and (now - last_run.replace(tzinfo=timezone.utc)).total_seconds() < agent.interval_seconds * 1.5
            ) if last_run else False
            nodes.append({
                "node_id":            agent.node_id,
                "name":               name,
                "status":             agent.status,
                "online":             online,
                "contribution_count": agent.contribution_count,
                "contribution_score": round(agent.contribution_score, 2),
                "run_count":          agent.run_count,
                "interval_seconds":   agent.interval_seconds,
            })
        total_score = sum(a.contribution_score for a in self._agents.values())
        return {
            "total_agents": len(self._agents),
            "online_agents": sum(1 for n in nodes if n["online"]),
            "total_contribution_score": round(total_score, 2),
            "nodes": nodes,
            "started_at": self._started_at.isoformat(),
        }
