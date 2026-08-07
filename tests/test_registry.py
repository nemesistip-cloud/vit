import pytest
import asyncio
from httpx import ASGITransport, AsyncClient

from main import app
from app.core.registry.manager import ModuleRegistry
from app.core.registry.models import ModuleMetadata, ModuleStatus, HealthStatus
from app.core.registry.contract import ModuleContract

class MockModule(ModuleContract):
    def __init__(self, mid, deps=[]):
        self._metadata = ModuleMetadata(
            module_id=mid,
            name=mid,
            owner="test",
            domain="test",
            dependencies=deps
        )
    @property
    def metadata(self): return self._metadata
    async def initialize(self, config): pass
    async def start(self): pass
    async def stop(self): pass
    async def check_health(self): return HealthStatus.HEALTHY
    async def get_diagnostics(self): return {}

@pytest.mark.asyncio
async def test_registration_and_discovery():
    reg = ModuleRegistry()
    m1 = MockModule("m1", deps=[])
    await reg.register(m1)

    assert reg.get_module("m1") == m1
    assert "m1" in reg.list_modules()

    # Discovery
    m1.metadata.capabilities = ["cap1"]
    results = reg.discover_by_capability("cap1")
    assert m1 in results

@pytest.mark.asyncio
async def test_idempotent_same_instance_registration():
    """Registering the exact same instance twice is a no-op (idempotent)."""
    reg = ModuleRegistry()
    m1 = MockModule("dup-same")
    await reg.register(m1)
    await reg.register(m1)  # should NOT raise


@pytest.mark.asyncio
async def test_duplicate_registration():
    """Registering a different instance with the same ID raises ValueError."""
    reg = ModuleRegistry()
    m1 = MockModule("dup")
    m2 = MockModule("dup")  # same module_id, different Python object
    await reg.register(m1)
    with pytest.raises(ValueError, match="Module duplication detected"):
        await reg.register(m2)

@pytest.mark.asyncio
async def test_dependency_validation():
    reg = ModuleRegistry()
    m1 = MockModule("base")
    m2 = MockModule("child", deps=["base"])
    await reg.register(m1)
    await reg.register(m2)
    reg.validate_dependencies() # Should pass

    m3 = MockModule("missing", deps=["nonexistent"])
    await reg.register(m3)
    with pytest.raises(ValueError, match="requires missing dependency"):
        reg.validate_dependencies()

@pytest.mark.asyncio
async def test_circular_dependency():
    reg = ModuleRegistry()
    m1 = MockModule("a", deps=["b"])
    m2 = MockModule("b", deps=["a"])
    await reg.register(m1)
    await reg.register(m2)
    with pytest.raises(ValueError, match="Circular dependency detected"):
        reg.validate_dependencies()


@pytest.mark.asyncio
async def test_registry_api_returns_expected_shape(monkeypatch):
    async def fake_probe(client, name, base_url):
        return {
            "status": "ok",
            "version": "test",
            "latency_ms": 12,
            "reachable": True,
        }

    monkeypatch.setattr("app.api.routes.registry._probe", fake_probe)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/registry")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"healthy", "degraded"}
    assert payload["services"]
    assert "gateway" in payload["services"]
    assert payload["services"]["gateway"]["url"].startswith("http")


@pytest.mark.asyncio
async def test_platform_status_api_returns_infrastructure_section(monkeypatch):
    async def fake_probe(client, name, base_url):
        return {
            "status": "ok",
            "version": "test",
            "latency_ms": 5,
            "reachable": True,
        }

    monkeypatch.setattr("app.api.routes.registry._probe", fake_probe)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"healthy", "degraded", "unhealthy"}
    assert payload["services"]["gateway"]["status"] == "ok"
    assert "infrastructure" in payload
    assert payload["infrastructure"]["database"]["status"] in {"connected", "disconnected"}
