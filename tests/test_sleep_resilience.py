import pytest
import time
from app.core.runtime.service_registry import service_registry, ServiceState, CircuitState
from app.core.runtime.service_client import SleepResilientClient, ServiceUnavailableError

@pytest.mark.asyncio
async def test_service_registry_initialization():
    services = service_registry.list_services()
    service_names = [s.service_name for s in services]
    assert "vitnetwork" in service_names
    assert "vit-chain" in service_names
    assert "vit-storage" in service_names
    assert "vit-ai" in service_names
    assert "vit-explorer" in service_names

@pytest.mark.asyncio
async def test_service_state_transition():
    service_registry.update_state("vit-ai", ServiceState.SLEEPING, last_error="HTTP 503")
    srv = service_registry.get_service("vit-ai")
    assert srv.state == ServiceState.SLEEPING
    assert srv.last_error == "HTTP 503"

    service_registry.update_state("vit-ai", ServiceState.ONLINE, duration_ms=120.0)
    srv = service_registry.get_service("vit-ai")
    assert srv.state == ServiceState.ONLINE
    assert srv.startup_duration_ms == 120.0

@pytest.mark.asyncio
async def test_circuit_breaker_opening():
    # Simulate repeated failures
    for _ in range(6):
        service_registry.update_state("vit-explorer", ServiceState.UNREACHABLE, last_error="Connection refused")

    srv = service_registry.get_service("vit-explorer")
    assert srv.circuit_state == CircuitState.OPEN

    client = SleepResilientClient("vit-explorer")
    with pytest.raises(ServiceUnavailableError):
        await client.execute_request("GET", "/health")
