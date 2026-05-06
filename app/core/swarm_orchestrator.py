"""app/core/swarm_orchestrator.py — VIT Swarm Orchestrator v6.0

Supervised agent coordinator that:
- Registers all 22 autonomous agents
- Monitors heartbeats every 30 seconds
- Auto-restarts crashed agents (configurable max restarts)
- Exposes a rich health/status API consumed by /health and /api/agents/*
- Integrates with the VIT Chain for contribution recording
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_GLOBAL_SWARM: Optional["SwarmOrchestrator"] = None


def get_swarm() -> "SwarmOrchestrator":
    global _GLOBAL_SWARM
    if _GLOBAL_SWARM is None:
        _GLOBAL_SWARM = SwarmOrchestrator()
    return _GLOBAL_SWARM


# ── Per-agent supervisor record ────────────────────────────────────────────────

class AgentRecord:
    def __init__(self, name: str, agent: Any, max_restarts: int = 10) -> None:
        self.name          = name
        self.agent         = agent
        self.max_restarts  = max_restarts
        self.restarts      = 0
        self.task: Optional[asyncio.Task] = None
        self.started_at    = datetime.now(timezone.utc)
        self.last_restart  = None

    def is_alive(self) -> bool:
        return self.task is not None and not self.task.done()

    def snapshot(self) -> dict:
        agent_snap = {}
        if hasattr(self.agent, "snapshot"):
            try:
                agent_snap = self.agent.snapshot()
            except Exception:
                pass
        return {
            "name":         self.name,
            "node_id":      getattr(self.agent, "node_id", f"did:vit:agent:{self.name}"),
            "alive":        self.is_alive(),
            "restarts":     self.restarts,
            "max_restarts": self.max_restarts,
            "started_at":   self.started_at.isoformat(),
            "last_restart": self.last_restart.isoformat() if self.last_restart else None,
            **agent_snap,
        }


# ── Swarm Orchestrator ─────────────────────────────────────────────────────────

class SwarmOrchestrator:
    """
    Supervised coordinator for all 22 autonomous VIT agents.

    Usage in lifespan:
        swarm = SwarmOrchestrator()
        await swarm.start_all()
        app.state.swarm = swarm
        yield
        await swarm.stop_all()
    """

    HEARTBEAT_INTERVAL = 30   # seconds between supervisor health checks

    def __init__(self, max_restarts: int = 10) -> None:
        global _GLOBAL_SWARM
        _GLOBAL_SWARM = self

        self._max_restarts  = max_restarts
        self._records: Dict[str, AgentRecord] = {}
        self._supervisor_task: Optional[asyncio.Task] = None
        self._started_at = datetime.now(timezone.utc)
        self._lock = asyncio.Lock()

        self._bootstrap_agents()
        logger.info("[swarm] orchestrator initialised with %d agents", len(self._records))

    def _bootstrap_agents(self) -> None:
        """Import and instantiate all 22 agents."""
        imports = [
            ("performance-monitor",  "app.agents.performance_monitor",         "PerformanceMonitorAgent"),
            ("weight-optimizer",     "app.agents.weight_optimizer",            "WeightOptimizerAgent"),
            ("retrain-trigger",      "app.agents.retrain_trigger",             "RetrainTriggerAgent"),
            ("match-scout",          "app.agents.match_scout_agent",           "MatchScoutAgent"),
            ("news-sentinel",        "app.agents.news_sentinel_agent",         "NewsSentinelAgent"),
            ("odds-anomaly",         "app.agents.odds_anomaly_agent",          "OddsAnomalyAgent"),
            ("kyc-screener",         "app.agents.kyc_screener_agent",          "KYCScreenerAgent"),
            ("fraud-review",         "app.agents.fraud_review_agent",          "FraudReviewAgent"),
            ("withdrawal-gatekeeper","app.agents.withdrawal_gatekeeper_agent", "WithdrawalGatekeeperAgent"),
            ("marketplace-audit",    "app.agents.marketplace_audit_agent",     "MarketplaceAuditAgent"),
            ("model-promoter",       "app.agents.model_promoter_agent",        "ModelPromoterAgent"),
            ("analytics-reporter",   "app.agents.analytics_reporter_agent",    "AnalyticsReporterAgent"),
            ("fixture-gap",          "app.agents.fixture_gap_agent",           "FixtureGapAgent"),
            ("accumulator-publisher","app.agents.accumulator_publisher_agent", "AccumulatorPublisherAgent"),
            ("revenue-optimizer",    "app.agents.revenue_optimizer_agent",     "RevenueOptimizerAgent"),
            ("governance-executor",  "app.agents.governance_executor_agent",   "GovernanceExecutorAgent"),
            ("self-healing",         "app.agents.self_healing_agent",          "SelfHealingAgent"),
            ("audit-sentinel",       "app.agents.audit_sentinel_agent",        "AuditSentinelAgent"),
            ("prediction-moderator", "app.agents.prediction_moderator_agent",  "PredictionModeratorAgent"),
            ("live-match-tracker",   "app.agents.live_match_tracker_agent",    "LiveMatchTrackerAgent"),
            ("oracle-node",          "app.agents.oracle_node_agent",           "OracleNodeAgent"),
            ("network-guardian",     "app.agents.network_guardian_agent",      "NetworkGuardianAgent"),
        ]

        for name, module_path, class_name in imports:
            try:
                import importlib
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                agent = cls()
                self._records[name] = AgentRecord(name, agent, self._max_restarts)
                logger.debug("[swarm] registered %s (%s)", name, class_name)
            except Exception as exc:
                logger.error("[swarm] failed to load agent %s: %s", name, exc)

    # ── Task spawning ──────────────────────────────────────────────────────────

    def _spawn_task(self, record: AgentRecord) -> None:
        """Create an asyncio task for one agent's loop."""
        if hasattr(record.agent, "loop"):
            record.task = asyncio.create_task(
                record.agent.loop(),
                name=f"swarm-{record.name}",
            )
        else:
            logger.warning("[swarm] agent %s has no .loop() method — skipping", record.name)

    async def start_all(self) -> None:
        """Launch all agent tasks and start the supervisor heartbeat."""
        async with self._lock:
            for record in self._records.values():
                self._spawn_task(record)
            logger.info("[swarm] spawned %d agent tasks", len(self._records))

        self._supervisor_task = asyncio.create_task(
            self._supervisor_loop(), name="swarm-supervisor"
        )
        logger.info("[swarm] supervisor heartbeat started (interval=%ss)", self.HEARTBEAT_INTERVAL)

    async def stop_all(self) -> None:
        """Cancel all tasks gracefully."""
        if self._supervisor_task and not self._supervisor_task.done():
            self._supervisor_task.cancel()

        tasks = [r.task for r in self._records.values() if r.task and not r.task.done()]
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("[swarm] all agent tasks stopped")

    # ── Supervisor heartbeat ────────────────────────────────────────────────────

    async def _supervisor_loop(self) -> None:
        """Monitor agent health and restart crashed agents."""
        while True:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                await self._check_and_restart()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("[swarm-supervisor] error: %s", exc)

    async def _check_and_restart(self) -> None:
        async with self._lock:
            for name, record in self._records.items():
                if record.is_alive():
                    continue
                if record.task and record.task.done():
                    exc = record.task.exception() if not record.task.cancelled() else None
                    if exc:
                        logger.error("[swarm] agent %s crashed: %s", name, exc)

                if record.restarts >= record.max_restarts:
                    logger.warning("[swarm] agent %s exceeded max restarts (%d) — not restarting",
                                   name, record.max_restarts)
                    continue

                record.restarts   += 1
                record.last_restart = datetime.now(timezone.utc)
                self._spawn_task(record)
                logger.info("[swarm] restarted agent %s (restart #%d)", name, record.restarts)

    # ── Public API ─────────────────────────────────────────────────────────────

    def trigger(self, agent_name: str) -> bool:
        """Manually trigger an immediate agent cycle."""
        record = self._records.get(agent_name)
        if record is None:
            return False
        if hasattr(record.agent, "trigger"):
            record.agent.trigger()
        return True

    def get_agent_result(self, agent_name: str) -> Optional[dict]:
        record = self._records.get(agent_name)
        if record is None:
            return None
        return getattr(record.agent, "last_result", None)

    def status(self) -> dict:
        """Full status snapshot for all agents."""
        alive   = sum(1 for r in self._records.values() if r.is_alive())
        stopped = len(self._records) - alive
        return {
            "orchestrator": {
                "started_at":   self._started_at.isoformat(),
                "total_agents": len(self._records),
                "alive":        alive,
                "stopped":      stopped,
                "heartbeat_interval_s": self.HEARTBEAT_INTERVAL,
            },
            "agents": {name: record.snapshot() for name, record in self._records.items()},
        }

    def health_summary(self) -> dict:
        """Compact summary suitable for /health endpoint."""
        alive         = sum(1 for r in self._records.values() if r.is_alive())
        total         = len(self._records)
        stopped_names = [n for n, r in self._records.items() if not r.is_alive()]
        return {
            "total":         total,
            "running":       alive,
            "stopped":       total - alive,
            "stopped_names": stopped_names,
        }

    def summary(self) -> list:
        """Lightweight list of one row per agent."""
        rows = []
        for name, record in self._records.items():
            agent = record.agent
            rows.append({
                "name":               name,
                "node_id":            getattr(agent, "node_id", f"did:vit:agent:{name}"),
                "status":             getattr(agent, "status", "unknown"),
                "alive":              record.is_alive(),
                "restarts":           record.restarts,
                "run_count":          getattr(agent, "run_count", 0),
                "error_count":        getattr(agent, "error_count", 0),
                "contribution_score": round(getattr(agent, "contribution_score", 0.0), 2),
                "last_run_at":        getattr(agent, "last_run_at", None) and agent.last_run_at.isoformat(),
                "last_error":         getattr(agent, "last_error", None),
                "interval_s":         getattr(agent, "interval_seconds", None),
            })
        return rows

    def network_summary(self) -> dict:
        """Network-focused node view."""
        now   = datetime.now(timezone.utc)
        nodes = []
        for name, record in self._records.items():
            agent    = record.agent
            last_run = getattr(agent, "last_run_at", None)
            interval = getattr(agent, "interval_seconds", 300)
            online   = (
                last_run is not None
                and (now - last_run.replace(tzinfo=timezone.utc)).total_seconds() < interval * 1.5
            ) if last_run else False
            nodes.append({
                "node_id":            getattr(agent, "node_id", f"did:vit:agent:{name}"),
                "name":               name,
                "online":             online,
                "alive":              record.is_alive(),
                "restarts":           record.restarts,
                "contribution_score": round(getattr(agent, "contribution_score", 0.0), 2),
                "run_count":          getattr(agent, "run_count", 0),
                "interval_s":         interval,
            })
        total_score = sum(getattr(r.agent, "contribution_score", 0.0) for r in self._records.values())
        return {
            "total_agents":            len(self._records),
            "online_agents":           sum(1 for n in nodes if n["online"]),
            "alive_agents":            sum(1 for n in nodes if n["alive"]),
            "total_contribution_score": round(total_score, 2),
            "nodes":                   nodes,
            "started_at":              self._started_at.isoformat(),
        }
