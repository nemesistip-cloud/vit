"""Central service watchdog with bounded detection and recovery state."""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


@dataclass
class ServiceState:
    name: str
    url: str
    health_path: str = "/health"
    state: str = "UNKNOWN"
    last_success: float | None = None
    last_failure: float | None = None
    last_recovery: float | None = None
    latency_ms: float | None = None
    consecutive_failures: int = 0
    deployment: str | None = None
    error: str | None = None
    recovery_attempts: int = 0
    incident_open: bool = False


@dataclass
class Watchdog:
    failure_threshold: int = 3
    recovery_cooldown_seconds: int = 300
    states: dict[str, ServiceState] = field(default_factory=dict)

    def register(self, name: str, url: str, health_path: str = "/health") -> None:
        self.states.setdefault(name, ServiceState(name=name, url=url.rstrip("/"), health_path=health_path))

    async def probe(self, name: str, client: httpx.AsyncClient | None = None) -> ServiceState:
        service = self.states[name]
        owns_client = client is None
        client = client or httpx.AsyncClient(timeout=10)
        started = time.monotonic()
        try:
            response = await client.get(f"{service.url}{service.health_path}")
            service.latency_ms = round((time.monotonic() - started) * 1000, 2)
            if response.status_code >= 500:
                raise RuntimeError(f"HTTP {response.status_code}")
            service.last_success = time.time()
            service.consecutive_failures = 0
            service.error = None
            service.state = "HEALTHY" if response.status_code == 200 else "DEGRADED"
        except Exception as exc:
            service.last_failure = time.time()
            service.consecutive_failures += 1
            service.error = type(exc).__name__
            if service.consecutive_failures >= self.failure_threshold:
                service.state = "UNHEALTHY"
            else:
                service.state = "DEGRADED"
        finally:
            if owns_client:
                await client.aclose()
        return service

    async def snapshot(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10) as client:
            await asyncio.gather(*(self.probe(name, client) for name in self.states))
        return [
            {
                "service": state.name,
                "state": state.state,
                "url": state.url,
                "last_success": state.last_success,
                "last_failure": state.last_failure,
                "last_recovery": state.last_recovery,
                "latency_ms": state.latency_ms,
                "consecutive_failures": state.consecutive_failures,
                "deployment": state.deployment,
                "error": state.error,
                "recovery_attempts": state.recovery_attempts,
            }
            for state in self.states.values()
        ]

    async def record_incidents(self, db: AsyncSession, snapshot: list[dict[str, Any]]) -> int:
        recorded = 0
        for item in snapshot:
            is_failure = item["state"] in {"DEGRADED", "UNHEALTHY"}
            state = self.states[item["service"]]
            if not is_failure and not state.incident_open:
                continue
            if is_failure and state.incident_open:
                continue
            db.add(AuditLog(
                action="watchdog.incident" if is_failure else "watchdog.recovered",
                actor="watchdog",
                resource="service",
                resource_id=item["service"],
                status=("warning" if item["state"] == "DEGRADED" else "failure") if is_failure else "ok",
                details={key: item[key] for key in ("state", "consecutive_failures", "latency_ms", "error")},
            ))
            state.incident_open = is_failure
            recorded += 1
        if recorded:
            await db.commit()
        return recorded

    def recovery_allowed(self, name: str) -> bool:
        state = self.states[name]
        if state.state != "UNHEALTHY":
            return False
        if state.last_recovery and time.time() - state.last_recovery < self.recovery_cooldown_seconds:
            return False
        return state.recovery_attempts < 2

    def mark_recovering(self, name: str) -> ServiceState:
        state = self.states[name]
        if not self.recovery_allowed(name):
            raise RuntimeError("Recovery threshold or cooldown prevents another attempt")
        state.state = "RECOVERING"
        state.recovery_attempts += 1
        state.last_recovery = time.time()
        return state


watchdog = Watchdog()
watchdog.register("gateway", os.getenv("VIT_GATEWAY_URL", "http://127.0.0.1:8000"), "/ping")
watchdog.register("ai", os.getenv("VIT_AI_URL", "https://vit-ai.onrender.com"))
watchdog.register("storage", os.getenv("VIT_STORAGE_URL", "https://vit-storage-4trt.onrender.com"))
watchdog.register("chain", os.getenv("VIT_CHAIN_URL", "https://vit-chain.onrender.com"))
watchdog.register("explorer", os.getenv("VIT_EXPLORER_URL", "https://vit-explorer.onrender.com"))
