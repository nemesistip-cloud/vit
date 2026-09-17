"""
Smoke tests for health / system endpoints.

These test the running FastAPI app via ASGI transport (no real DB needed
since these endpoints don't touch the database).
"""
import pytest


@pytest.mark.asyncio
async def test_ping(client):
    resp = await client.get("/ping")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_root_does_not_expose_internals(client):
    """The root / endpoint must not expose version, env, or subsystem names."""
    resp = await client.get("/")
    assert resp.status_code == 200
    text = resp.text
    # Must not expose environment names or subsystem details
    assert "subsystem" not in text.lower()
    assert "development" not in text.lower()
    assert "production" not in text.lower()
    # Version badge is OK as long as it's not exposing internal build paths
    # (the version number itself is fine in the response)


@pytest.mark.asyncio
async def test_docs_accessible(client):
    resp = await client.get("/docs")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_openapi_json(client):
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema


@pytest.mark.asyncio
async def test_readiness_uses_shared_redis_client(client, monkeypatch):
    """Readiness must detect Redis when only the shared client is configured."""
    from app.core import redis as redis_module

    class HealthyRedis:
        async def ping(self):
            return True

    monkeypatch.setattr(redis_module, "redis_client", HealthyRedis())
    response = await client.get("/readiness")

    assert response.status_code == 200
    assert response.json()["redis"] is True


@pytest.mark.asyncio
async def test_health_treats_optional_kernel_degradation_as_nonfatal(monkeypatch):
    """Database connectivity and model readiness should remain the core health signals."""
    import main

    class FakeKernel:
        def get_status(self):
            return {"kernel_state": "DEGRADED"}

    class FakeOrchestrator:
        def num_models_ready(self):
            return 13

    class FakeConnection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, *args, **kwargs):
            return None

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    monkeypatch.setattr(main, "kernel", FakeKernel())
    monkeypatch.setattr(main, "get_orchestrator", lambda: FakeOrchestrator())
    monkeypatch.setattr(main, "engine", FakeEngine())

    response = await main.health()

    assert response.status == "ok"
    assert response.db_connected is True
    assert response.models_loaded == 13
