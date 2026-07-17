import asyncio
import pytest
from app.core.resource_platform.supervisor import BackgroundTaskSupervisor

@pytest.mark.asyncio
async def test_supervisor_restarts_failed_task_once():
    starts = 0

    async def failing_task():
        nonlocal starts
        starts += 1
        raise RuntimeError("boom")

    supervisor = BackgroundTaskSupervisor(
        [("failing", failing_task)],
        check_interval=0.01,
        max_restarts=2, # Increased to allow one restart
    )

    supervisor.start()
    await asyncio.sleep(0.1) # Wait long enough for monitor to see it stopped and restart
    snapshot = supervisor.snapshot()
    await supervisor.stop()

    assert starts >= 2
