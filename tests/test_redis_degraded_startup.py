from __future__ import annotations

from types import SimpleNamespace

import pytest
import logging

from app.core import redis as redis_module
from app.core.event_bus import EventBus


class _FailingRedisClient:
    def __init__(self):
        self.closed = False

    async def ping(self):
        raise TimeoutError("simulated Redis timeout; credential=must-not-be-logged")

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_production_redis_timeout_closes_client_and_fails_closed(monkeypatch):
    client = _FailingRedisClient()
    monkeypatch.setenv("REDIS_URL", "redis://redis.example.invalid:6379")
    monkeypatch.setattr(redis_module, "ENVIRONMENT", "production")
    monkeypatch.setattr(redis_module, "build_redis_client", lambda *_args, **_kwargs: client)

    app = SimpleNamespace(state=SimpleNamespace(redis=None))
    with pytest.raises(RuntimeError, match="Redis connection failed") as error:
        await redis_module.require_redis(
            app,
            socket_connect_timeout=0.1,
            socket_timeout=0.1,
            ping_timeout=0.2,
        )

    assert client.closed is True
    assert redis_module.redis_client is None
    assert "must-not-be-logged" not in str(error.value)


@pytest.mark.asyncio
async def test_production_redis_timeout_logs_only_exception_type(monkeypatch, caplog):
    client = _FailingRedisClient()
    monkeypatch.setenv("REDIS_URL", "redis://redis.example.invalid:6379")
    monkeypatch.setattr(redis_module, "ENVIRONMENT", "production")
    monkeypatch.setattr(redis_module, "build_redis_client", lambda *_args, **_kwargs: client)

    with caplog.at_level(logging.CRITICAL, logger="app.core.redis"):
        with pytest.raises(RuntimeError):
            await redis_module.require_redis(
                SimpleNamespace(state=SimpleNamespace(redis=None)),
                socket_connect_timeout=0.1,
                socket_timeout=0.1,
                ping_timeout=0.2,
            )

    assert "must-not-be-logged" not in caplog.text
    assert "TimeoutError" in caplog.text


@pytest.mark.asyncio
async def test_kernel_redis_subsystem_degrades_without_raising(monkeypatch):
    async def fail_redis(_app, **_kwargs):
        raise RuntimeError("simulated Redis timeout")

    monkeypatch.setattr(redis_module, "require_redis", fail_redis)
    from app.core.subsystems import RedisSubsystem

    subsystem = RedisSubsystem(None)
    await subsystem._on_start()
    assert subsystem.name == "redis"
    assert await subsystem.health_check() is False


@pytest.mark.asyncio
async def test_kernel_redis_subsystem_recovers_when_ping_succeeds(monkeypatch):
    class _HealthyClient:
        async def ping(self):
            return True

    monkeypatch.setattr(redis_module, "redis_client", _HealthyClient())
    from app.core.subsystems import RedisSubsystem

    assert await RedisSubsystem(None).health_check() is True


@pytest.mark.asyncio
async def test_resource_platform_initialization_does_not_probe_redis(monkeypatch):
    async def unexpected_probe(*_args, **_kwargs):
        raise AssertionError("ResourcePlatform must not probe Redis during initialization")

    monkeypatch.setattr(redis_module, "require_redis", unexpected_probe)
    from app.core.resource_platform.subsystem import ResourcePlatformSubsystem

    subsystem = ResourcePlatformSubsystem(None)
    await subsystem._on_initialize({})
    assert subsystem._disabled_reason is None


@pytest.mark.asyncio
async def test_resource_platform_skips_queue_workers_when_redis_unavailable(monkeypatch):
    monkeypatch.setattr(redis_module, "redis_client", None)
    from app.core.resource_platform.subsystem import ResourcePlatformSubsystem

    subsystem = ResourcePlatformSubsystem(None)
    await subsystem._on_start()
    assert subsystem._disabled_reason == "Redis unavailable"
    assert subsystem.worker_manager is None
    assert subsystem.scheduler is None


@pytest.mark.asyncio
async def test_event_bus_reuses_shared_redis_client(monkeypatch):
    class _HealthyClient:
        async def ping(self):
            return True

    client = _HealthyClient()
    monkeypatch.setenv("REDIS_URL", "redis://redis.example.invalid:6379")
    monkeypatch.setattr(redis_module, "redis_client", client)
    bus = EventBus()
    bus._redis = None
    bus._redis_enabled = False

    await bus.connect_redis()

    assert bus._redis is client
    assert bus._redis_enabled is True


@pytest.mark.asyncio
async def test_event_bus_does_not_retry_new_redis_connection(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://redis.example.invalid:6379")
    monkeypatch.setattr(redis_module, "redis_client", None)

    def forbidden_client(*_args, **_kwargs):
        raise AssertionError("event bus must not open another Redis client")

    monkeypatch.setattr(redis_module, "build_redis_client", forbidden_client)
    bus = EventBus()
    bus._redis = None
    bus._redis_enabled = False

    await bus.connect_redis()

    assert bus._redis is None
    assert bus._redis_enabled is False
