"""
app/core/runtime/service_registry.py

Service Registry for VIT Platform microservices with sleep-tolerance metadata,
circuit breaker state, retry policy, and startup timeout support for Render Free Plan compatibility.
"""

from __future__ import annotations

import os
import time
import logging
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ServiceCriticality(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    OPTIONAL = "OPTIONAL"

class ServiceState(str, Enum):
    UNKNOWN = "UNKNOWN"
    ONLINE = "ONLINE"
    SLEEPING = "SLEEPING"
    WAKING = "WAKING"
    DEGRADED = "DEGRADED"
    UNREACHABLE = "UNREACHABLE"

class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class RetryPolicy(BaseModel):
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0

class ServiceDefinition(BaseModel):
    service_name: str
    url: str
    health_endpoint: str = "/health"
    ready_endpoint: str = "/ready"
    criticality: ServiceCriticality = ServiceCriticality.MEDIUM
    startup_timeout: float = 60.0  # Cold-start grace period in seconds
    sleep_tolerance: bool = True   # True if service is allowed/expected to spin down on free tier
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)

    # Dynamic status properties
    state: ServiceState = ServiceState.UNKNOWN
    circuit_state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    last_state_change: float = Field(default_factory=time.time)
    last_successful_check: float = 0.0
    last_health_check: float = 0.0
    last_error: Optional[str] = None
    startup_duration_ms: float = 0.0

class ServiceRegistry:
    _instance: Optional[ServiceRegistry] = None

    def __new__(cls) -> ServiceRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
            cls._instance._init_default_services()
        return cls._instance

    def _init_default_services(self) -> None:
        port = os.getenv("PORT", "5000")
        gateway_url = os.getenv("VITNETWORK_URL", f"http://localhost:{port}").rstrip("/")

        tachyon_base = os.getenv("TACHYON_URL", "").rstrip("/")
        tachyon_url = tachyon_base or os.getenv("TACHYON_ENDPOINT", "https://vit-storage-4trt.onrender.com").rstrip("/")

        chain_url = os.getenv("VIT_CHAIN_URL", "https://vit-chain.onrender.com").rstrip("/")
        ai_url = os.getenv("VIT_AI_URL", "https://vit-ai.onrender.com").rstrip("/")
        explorer_url = os.getenv("VIT_EXPLORER_URL", "https://vit-explorer.onrender.com").rstrip("/")

        defaults = [
            ServiceDefinition(
                service_name="vitnetwork",
                url=gateway_url,
                health_endpoint="/ping",
                ready_endpoint="/ready",
                criticality=ServiceCriticality.CRITICAL,
                startup_timeout=30.0,
                sleep_tolerance=False,
            ),
            ServiceDefinition(
                service_name="vit-chain",
                url=chain_url,
                health_endpoint="/health",
                ready_endpoint="/ready",
                criticality=ServiceCriticality.HIGH,
                startup_timeout=60.0,
                sleep_tolerance=True,
            ),
            ServiceDefinition(
                service_name="vit-storage",
                url=tachyon_url,
                health_endpoint="/status",
                ready_endpoint="/health",
                criticality=ServiceCriticality.MEDIUM,
                startup_timeout=60.0,
                sleep_tolerance=True,
            ),
            ServiceDefinition(
                service_name="vit-ai",
                url=ai_url,
                health_endpoint="/health",
                ready_endpoint="/ready",
                criticality=ServiceCriticality.MEDIUM,
                startup_timeout=60.0,
                sleep_tolerance=True,
            ),
            ServiceDefinition(
                service_name="vit-explorer",
                url=explorer_url,
                health_endpoint="/health",
                ready_endpoint="/ready",
                criticality=ServiceCriticality.LOW,
                startup_timeout=45.0,
                sleep_tolerance=True,
            ),
        ]

        for srv in defaults:
            self._services[srv.service_name] = srv

    def get_service(self, service_name: str) -> Optional[ServiceDefinition]:
        return self._services.get(service_name)

    def register_service(self, definition: ServiceDefinition) -> None:
        self._services[definition.service_name] = definition

    def list_services(self) -> List[ServiceDefinition]:
        return list(self._services.values())

    def update_state(
        self,
        service_name: str,
        state: ServiceState,
        last_error: Optional[str] = None,
        duration_ms: float = 0.0,
    ) -> None:
        srv = self._services.get(service_name)
        if not srv:
            return

        now = time.time()
        srv.state = state
        srv.last_health_check = now
        if state == ServiceState.ONLINE:
            srv.last_successful_check = now
            srv.failure_count = 0
            if srv.circuit_state != CircuitState.CLOSED:
                srv.circuit_state = CircuitState.CLOSED
                srv.last_state_change = now
            if duration_ms > 0:
                srv.startup_duration_ms = duration_ms
        elif state in (ServiceState.UNREACHABLE, ServiceState.DEGRADED, ServiceState.SLEEPING):
            if last_error:
                srv.last_error = last_error
            srv.failure_count += 1
            if srv.failure_count >= srv.failure_threshold and srv.circuit_state == CircuitState.CLOSED:
                srv.circuit_state = CircuitState.OPEN
                srv.last_state_change = now
                logger.warning(
                    f"[ServiceRegistry] Circuit OPENED for {service_name} after {srv.failure_count} failures."
                )

    def record_circuit_attempt(self, service_name: str) -> bool:
        srv = self._services.get(service_name)
        if not srv:
            return True

        now = time.time()
        if srv.circuit_state == CircuitState.OPEN:
            if now - srv.last_state_change > srv.recovery_timeout:
                srv.circuit_state = CircuitState.HALF_OPEN
                srv.last_state_change = now
                logger.info(f"[ServiceRegistry] Circuit HALF-OPEN for {service_name}. Trying probe request.")
                return True
            return False
        return True

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "services": {
                name: srv.dict()
                for name, srv in self._services.items()
            }
        }

service_registry = ServiceRegistry()
