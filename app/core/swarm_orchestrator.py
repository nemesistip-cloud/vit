"""app/core/swarm_orchestrator.py — VIT Swarm Orchestrator v7.0

Supervised agent coordinator that:
- Registers all 22 autonomous agents
- Monitors heartbeats every 20 seconds (down from 30 s)
- Auto-restarts crashed agents (configurable max restarts)
- Exposes a rich health/status API consumed by /health and /api/agents/*
- Cross-agent event bus: agents can emit typed events; others subscribe
- Efficiency score per agent: run_count / (run_count + error_count)
- Leaderboard: agents ranked by contribution_score
"""
from __future__ import annotations

import asyncio
import collections
import logging
import time
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

_GLOBAL_SWARM: Optional["SwarmOrchestrator"] = None
_MAX_BUS_EVENTS = 200   # ring-buffer size for cross-agent event bus


def get_swarm() -> "SwarmOrchestrator":
    """Return the global SwarmOrchestrator. Must be initialised via set_swarm() at startup."""
    if _GLOBAL_SWARM is None:
        raise RuntimeError(
            "SwarmOrchestrator has not been initialised. "
            "Call set_swarm() or instantiate SwarmOrchestrator before using get_swarm()."
        )
    return _GLOBAL_SWARM


def set_swarm(instance: "SwarmOrchestrator") -> None:
    """Register the global SwarmOrchestrator instance (called from app lifespan)."""
    global _GLOBAL_SWARM
    _GLOBAL_SWARM = instance


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

    def efficiency_score(self) -> float:
        """Fraction of cycles that succeeded: run_count / (run_count + error_count).
        Returns 1.0 for fresh agents (no cycles yet)."""
        agent   = self.agent
        runs    = getattr(agent, "run_count",   0)
        errors  = getattr(agent, "error_count", 0)
        total   = runs + errors
        return round(runs / total, 4) if total > 0 else 1.0

    def snapshot(self) -> dict:
        agent_snap = {}
        if hasattr(self.agent, "snapshot"):
            try:
                agent_snap = self.agent.snapshot()
            except Exception:
                pass
        return {
            "name":             self.name,
            "node_id":          getattr(self.agent, "node_id", f"did:vit:agent:{self.name}"),
            "alive":            self.is_alive(),
            "restarts":         self.restarts,
            "max_restarts":     self.max_restarts,
            "efficiency_score": self.efficiency_score(),
            "started_at":       self.started_at.isoformat(),
            "last_restart":     self.last_restart.isoformat() if self.last_restart else None,
            **agent_snap,
        }


# ── Cross-agent event bus record ───────────────────────────────────────────────

class SwarmEvent:
    __slots__ = ("event_type", "source", "data", "emitted_at")

    def __init__(self, event_type: str, source: str, data: dict) -> None:
        self.event_type = event_type
        self.source     = source
        self.data       = data
        self.emitted_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "source":     self.source,
            "data":       self.data,
            "emitted_at": self.emitted_at.isoformat(),
        }


# ── Swarm Orchestrator ─────────────────────────────────────────────────────────

class SwarmOrchestrator:
    """
    Supervised coordinator for all 22 autonomous VIT agents — v7.0.

    New in v7.0:
    - Heartbeat every 20 s (was 30 s) for faster crash detection
    - Cross-agent event bus (ring buffer, last 200 events)
    - Per-agent efficiency_score (run success rate)
    - Agent leaderboard sorted by contribution_score
    """

    HEARTBEAT_INTERVAL = 20   # seconds between supervisor health checks

    def __init__(self, max_restarts: int = 10) -> None:
        global _GLOBAL_SWARM
        _GLOBAL_SWARM = self

        self._max_restarts  = max_restarts
        self._records: Dict[str, AgentRecord] = {}
        self._supervisor_task: Optional[asyncio.Task] = None
        self._started_at = datetime.now(timezone.utc)
        self._lock  = asyncio.Lock()

        # Cross-agent event bus
        self._event_bus: Deque[SwarmEvent] = collections.deque(maxlen=_MAX_BUS_EVENTS)
        self._bus_lock  = asyncio.Lock()

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
                mod   = importlib.import_module(module_path)
                cls   = getattr(mod, class_name)
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
        """Monitor agent health and restart crashed agents every HEARTBEAT_INTERVAL s."""
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
                        await self.emit_event("agent_crashed", name, {"error": str(exc)})

                if record.restarts >= record.max_restarts:
                    logger.warning(
                        "[swarm] agent %s exceeded max restarts (%d) — not restarting",
                        name, record.max_restarts,
                    )
                    continue

                record.restarts    += 1
                record.last_restart = datetime.now(timezone.utc)
                self._spawn_task(record)
                logger.info("[swarm] restarted agent %s (restart #%d)", name, record.restarts)
                await self.emit_event("agent_restarted", name, {"restart_count": record.restarts})

    # ── Cross-agent event bus ──────────────────────────────────────────────────

    async def emit_event(self, event_type: str, source: str, data: dict) -> None:
        """Broadcast a typed event onto the swarm bus (fire-and-forget, non-blocking)."""
        event = SwarmEvent(event_type=event_type, source=source, data=data)
        async with self._bus_lock:
            self._event_bus.append(event)
        logger.debug("[swarm-bus] %s from %s: %s", event_type, source, data)

    def get_events(
        self,
        since: Optional[datetime] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        """Return recent bus events, optionally filtered by time or type."""
        events = list(self._event_bus)
        if since:
            events = [e for e in events if e.emitted_at >= since]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [e.to_dict() for e in events[-limit:]]

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
                "started_at":           self._started_at.isoformat(),
                "total_agents":         len(self._records),
                "alive":                alive,
                "stopped":              stopped,
                "heartbeat_interval_s": self.HEARTBEAT_INTERVAL,
                "bus_events_buffered":  len(self._event_bus),
            },
            "agents": {name: record.snapshot() for name, record in self._records.items()},
        }

    def health_summary(self) -> dict:
        """Compact summary suitable for /health endpoint."""
        alive         = sum(1 for r in self._records.values() if r.is_alive())
        total         = len(self._records)
        stopped_names = [n for n, r in self._records.items() if not r.is_alive()]
        avg_efficiency = (
            sum(r.efficiency_score() for r in self._records.values()) / total
            if total else 0.0
        )
        return {
            "total":            total,
            "running":          alive,
            "stopped":          total - alive,
            "stopped_names":    stopped_names,
            "avg_efficiency":   round(avg_efficiency, 4),
        }

    def summary(self) -> list:
        """Lightweight list of one row per agent, with efficiency score."""
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
                "efficiency_score":   record.efficiency_score(),
                "contribution_score": round(getattr(agent, "contribution_score", 0.0), 2),
                "last_run_at":        (
                    agent.last_run_at.isoformat()
                    if getattr(agent, "last_run_at", None) else None
                ),
                "last_error":         getattr(agent, "last_error", None),
                "interval_s":         getattr(agent, "interval_seconds", None),
            })
        return rows

    def leaderboard(self, top_n: int = 10) -> list:
        """Agents ranked by lifetime contribution_score (descending)."""
        rows = []
        for name, record in self._records.items():
            agent = record.agent
            rows.append({
                "rank":               0,   # filled below
                "name":               name,
                "node_id":            getattr(agent, "node_id", f"did:vit:agent:{name}"),
                "contribution_score": round(getattr(agent, "contribution_score", 0.0), 2),
                "run_count":          getattr(agent, "run_count", 0),
                "efficiency_score":   record.efficiency_score(),
                "alive":              record.is_alive(),
            })
        rows.sort(key=lambda r: r["contribution_score"], reverse=True)
        for i, row in enumerate(rows[:top_n], start=1):
            row["rank"] = i
        return rows[:top_n]

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
                "efficiency_score":   record.efficiency_score(),
                "run_count":          getattr(agent, "run_count", 0),
                "interval_s":         interval,
            })
        total_score = sum(getattr(r.agent, "contribution_score", 0.0) for r in self._records.values())
        return {
            "total_agents":             len(self._records),
            "online_agents":            sum(1 for n in nodes if n["online"]),
            "alive_agents":             sum(1 for n in nodes if n["alive"]),
            "total_contribution_score": round(total_score, 2),
            "avg_efficiency":           round(
                sum(r.efficiency_score() for r in self._records.values()) / max(len(self._records), 1),
                4,
            ),
            "nodes":      nodes,
            "started_at": self._started_at.isoformat(),
        }
