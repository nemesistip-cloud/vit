import pytest
from unittest.mock import MagicMock, AsyncMock
from app.core.resource_platform.subsystem import ResourcePlatformSubsystem

@pytest.mark.asyncio
async def test_subsystem_lifecycle():
    kernel = MagicMock()
    subsystem = ResourcePlatformSubsystem(kernel)

    # Bypass actual Redis connection in tests
    subsystem._on_initialize = AsyncMock()
    subsystem._on_start = AsyncMock()
    subsystem._on_stop = AsyncMock()

    await subsystem.initialize({})
    assert subsystem._on_initialize.called

    await subsystem.start()
    assert subsystem._on_start.called

    await subsystem.stop()
    assert subsystem._on_stop.called
