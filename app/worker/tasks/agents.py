"""app/worker/tasks/agents.py — Celery tasks wrapping autonomous agents.

Each task:
  - Runs agent.run_cycle() inside asyncio.run() (sync wrapper for async logic)
  - Posts Redis heartbeat at agent:heartbeat:{name} with 120s TTL
  - Logs structured JSON on start / ok / error
  - max_retries=3, exponential backoff
"""
from __future__ import annotations

import asyncio
import importlib
import json
import logging
import time
from typing import Any, Dict

from celery import Task
from celery.utils.log import get_task_logger

from app.worker.celery_app import celery

logger = get_task_logger(__name__)


def _heartbeat(name: str, status: str, detail: Dict[str, Any]) -> None:
    """Write agent heartbeat to Redis. Silent on any failure."""
    try:
        import os, redis as _r
        r = _r.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
        r.setex(f"agent:heartbeat:{name}", 120,
                json.dumps({"agent": name, "status": status,
                            "ts": time.time(), **detail}))
        r.close()
    except Exception:
        pass


def _run(module: str, cls_name: str) -> Dict[str, Any]:
    """Import agent class, instantiate, and run one cycle synchronously."""
    mod = importlib.import_module(module)
    agent = getattr(mod, cls_name)()
    return asyncio.run(agent.run_cycle())


class _AgentTask(Task):
    abstract = True
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        _heartbeat(getattr(self, "_agent_name", self.name), "error", {"error": str(exc)})


@celery.task(name="agents.run_prediction", base=_AgentTask,
             max_retries=3, default_retry_delay=60,
             autoretry_for=(Exception,), retry_backoff=True)
def run_prediction_agent():
    """PerformanceMonitorAgent — tracks ML model accuracy metrics."""
    name = "performance-monitor"
    _heartbeat(name, "running", {})
    t0 = time.time()
    try:
        r = _run("app.agents.performance_monitor", "PerformanceMonitorAgent")
        _heartbeat(name, "ok", {"elapsed_s": round(time.time() - t0, 2)})
        return r
    except Exception as exc:
        _heartbeat(name, "error", {"error": str(exc)}); raise


@celery.task(name="agents.oracle_sentinel", base=_AgentTask,
             max_retries=3, default_retry_delay=30,
             autoretry_for=(Exception,), retry_backoff=True)
def run_oracle_sentinel():
    """OracleNodeAgent — submits oracle results and monitors consensus."""
    name = "oracle-node"
    _heartbeat(name, "running", {})
    t0 = time.time()
    try:
        r = _run("app.agents.oracle_node_agent", "OracleNodeAgent")
        _heartbeat(name, "ok", {"elapsed_s": round(time.time() - t0, 2)})
        return r
    except Exception as exc:
        _heartbeat(name, "error", {"error": str(exc)}); raise


@celery.task(name="agents.market_scout", base=_AgentTask,
             max_retries=3, default_retry_delay=120,
             autoretry_for=(Exception,), retry_backoff=True)
def run_market_scout():
    """MatchScoutAgent — discovers fixtures and enriches match data."""
    name = "match-scout"
    _heartbeat(name, "running", {})
    t0 = time.time()
    try:
        r = _run("app.agents.match_scout_agent", "MatchScoutAgent")
        _heartbeat(name, "ok", {"elapsed_s": round(time.time() - t0, 2)})
        return r
    except Exception as exc:
        _heartbeat(name, "error", {"error": str(exc)}); raise


@celery.task(name="agents.merit_calculator", base=_AgentTask,
             max_retries=2, default_retry_delay=300,
             autoretry_for=(Exception,), retry_backoff=True)
def run_merit_calculator():
    """WeightOptimizerAgent — recalculates merit scores and model weights."""
    name = "weight-optimizer"
    _heartbeat(name, "running", {})
    t0 = time.time()
    try:
        r = _run("app.agents.weight_optimizer", "WeightOptimizerAgent")
        _heartbeat(name, "ok", {"elapsed_s": round(time.time() - t0, 2)})
        return r
    except Exception as exc:
        _heartbeat(name, "error", {"error": str(exc)}); raise


@celery.task(name="agents.fraud_review", base=_AgentTask,
             max_retries=3, default_retry_delay=60,
             autoretry_for=(Exception,), retry_backoff=True)
def run_fraud_review():
    """FraudReviewAgent — evaluates transactions, flags suspicious activity."""
    name = "fraud-review"
    _heartbeat(name, "running", {})
    t0 = time.time()
    try:
        r = _run("app.agents.fraud_review_agent", "FraudReviewAgent")
        _heartbeat(name, "ok", {"elapsed_s": round(time.time() - t0, 2)})
        return r
    except Exception as exc:
        _heartbeat(name, "error", {"error": str(exc)}); raise


@celery.task(name="agents.audit_sentinel", base=_AgentTask,
             max_retries=2, default_retry_delay=180,
             autoretry_for=(Exception,), retry_backoff=True)
def run_audit_sentinel():
    """AuditSentinelAgent — monitors audit logs for anomalies."""
    name = "audit-sentinel"
    _heartbeat(name, "running", {})
    t0 = time.time()
    try:
        r = _run("app.agents.audit_sentinel_agent", "AuditSentinelAgent")
        _heartbeat(name, "ok", {"elapsed_s": round(time.time() - t0, 2)})
        return r
    except Exception as exc:
        _heartbeat(name, "error", {"error": str(exc)}); raise


@celery.task(name="agents.withdrawal_gate", base=_AgentTask,
             max_retries=3, default_retry_delay=30,
             autoretry_for=(Exception,), retry_backoff=True)
def run_withdrawal_gatekeeper():
    """WithdrawalGatekeeperAgent — enforces withdrawal fraud rules."""
    name = "withdrawal-gatekeeper"
    _heartbeat(name, "running", {})
    t0 = time.time()
    try:
        r = _run("app.agents.withdrawal_gatekeeper_agent",
                 "WithdrawalGatekeeperAgent")
        _heartbeat(name, "ok", {"elapsed_s": round(time.time() - t0, 2)})
        return r
    except Exception as exc:
        _heartbeat(name, "error", {"error": str(exc)}); raise


@celery.task(name="agents.tachyon_health", base=_AgentTask,
             max_retries=2, default_retry_delay=300,
             autoretry_for=(Exception,), retry_backoff=True)
def run_tachyon_health():
    """NetworkGuardianAgent — checks Tachyon storage and network health."""
    name = "network-guardian"
    _heartbeat(name, "running", {})
    t0 = time.time()
    try:
        r = _run("app.agents.network_guardian_agent", "NetworkGuardianAgent")
        _heartbeat(name, "ok", {"elapsed_s": round(time.time() - t0, 2)})
        return r
    except Exception as exc:
        _heartbeat(name, "error", {"error": str(exc)}); raise
