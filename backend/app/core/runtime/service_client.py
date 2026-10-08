"""
app/core/runtime/service_client.py

Sleep-resilient HTTP client wrapper that handles cold-start waiting with
exponential backoff, circuit breaking, and graceful degradation for downstream microservices.
"""

from __future__ import annotations

import os
import time
import logging
import asyncio
import httpx
from typing import Optional, Dict, Any

from app.core.runtime.service_registry import (
    service_registry,
    ServiceState,
    CircuitState,
    ServiceDefinition,
)

logger = logging.getLogger(__name__)

class ServiceUnavailableError(Exception):
    """Raised when a target service cannot be reached or is in cold-start timeout."""
    pass

class SleepResilientClient:
    """
    Central client wrapper for interacting with VIT microservices.
    Automatically detects sleeping services, waits during cold-starts with backoff,
    and updates the ServiceRegistry.
    """

    def __init__(self, service_name: str, timeout: float = 30.0):
        self.service_name = service_name
        self.timeout = timeout

    def _get_definition(self) -> ServiceDefinition:
        definition = service_registry.get_service(self.service_name)
        if not definition:
            raise ValueError(f"Service '{self.service_name}' is not registered in ServiceRegistry.")
        return definition

    def _get_auth_headers(self) -> Dict[str, str]:
        from app.core.service_auth import make_service_headers
        headers = make_service_headers("vitnetwork")
        api_key = (
            os.getenv("VIT_STORAGE_API_KEY")
            or os.getenv("TACHYON_API_KEY")
            or os.getenv("VIT_AI_API_KEY")
        )
        if api_key:
            headers["X-API-Key"] = api_key
            headers["X-API-KEY"] = api_key
        return headers

    async def check_readiness(self) -> bool:
        """Poll the ready endpoint to confirm the service is awake."""
        definition = self._get_definition()
        url = f"{definition.url.rstrip('/')}{definition.ready_endpoint}"
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, headers=self._get_auth_headers())
                duration_ms = (time.time() - start_time) * 1000.0
                if res.status_code == 200:
                    service_registry.update_state(self.service_name, ServiceState.ONLINE, duration_ms=duration_ms)
                    return True
                elif res.status_code in (502, 503, 504):
                    service_registry.update_state(self.service_name, ServiceState.SLEEPING, last_error=f"HTTP {res.status_code}")
                    return False
                else:
                    service_registry.update_state(self.service_name, ServiceState.DEGRADED, last_error=f"HTTP {res.status_code}")
                    return False
        except Exception as exc:
            service_registry.update_state(self.service_name, ServiceState.UNREACHABLE, last_error=str(exc))
            return False

    async def execute_request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> httpx.Response:
        """
        Execute an HTTP request against the target service with backoff for cold starts.
        """
        definition = self._get_definition()
        if not service_registry.record_circuit_attempt(self.service_name):
            raise ServiceUnavailableError(
                f"Circuit breaker is OPEN for service '{self.service_name}'. Request blocked."
            )

        target_url = f"{definition.url.rstrip('/')}/{path.lstrip('/')}"
        policy = definition.retry_policy
        start_time = time.time()
        last_exception = None

        headers = self._get_auth_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        for attempt in range(policy.max_retries + 1):
            try:
                if attempt > 0:
                    service_registry.update_state(self.service_name, ServiceState.WAKING)

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(method, target_url, headers=headers, **kwargs)

                if response.status_code in (200, 201, 202, 204):
                    duration_ms = (time.time() - start_time) * 1000.0
                    service_registry.update_state(self.service_name, ServiceState.ONLINE, duration_ms=duration_ms)
                    return response

                # Non-retriable client errors
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    service_registry.update_state(self.service_name, ServiceState.ONLINE)
                    return response

                # Service waking / upstream gateway issue (502, 503, 504, 429)
                last_exception = RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
                service_registry.update_state(
                    self.service_name, ServiceState.SLEEPING, last_error=str(last_exception)
                )

            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError) as exc:
                last_exception = exc
                service_registry.update_state(
                    self.service_name, ServiceState.SLEEPING, last_error=str(exc)
                )

            if attempt < policy.max_retries:
                delay = min(
                    policy.initial_delay * (policy.backoff_factor ** attempt),
                    policy.max_delay,
                )
                logger.info(
                    f"[SleepResilientClient] Service '{self.service_name}' unresponsive on attempt {attempt+1}. "
                    f"Waiting {delay:.1f}s for cold-start..."
                )
                await asyncio.sleep(delay)

        service_registry.update_state(
            self.service_name, ServiceState.UNREACHABLE, last_error=str(last_exception)
        )
        raise ServiceUnavailableError(
            f"Service '{self.service_name}' failed to wake up or respond after {policy.max_retries} attempts. Last error: {last_exception}"
        )
