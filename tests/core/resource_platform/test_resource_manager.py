import pytest
import asyncio
from app.core.resource_platform.resources import ResourceManager
from app.core.resource_platform.models import ResourceQuota

@pytest.mark.asyncio
async def test_resource_allocation():
    rm = ResourceManager()
    quota = ResourceQuota(cpu_cores=0.5, memory_mb=256)

    # Successful allocation
    success = await rm.allocate("task-1", quota)
    assert success is True

    util = await rm.get_utilization()
    assert util["allocated_tasks_count"] == 1
    assert util["tracked_cpu_cores"] == 0.5
    assert util["tracked_memory_mb"] == 256

    # Release
    await rm.release("task-1")
    util = await rm.get_utilization()
    assert util["allocated_tasks_count"] == 0
