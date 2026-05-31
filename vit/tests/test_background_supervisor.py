import asyncio

import pytest

from main import BackgroundTaskSupervisor


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
        max_restarts=1,
    )

    supervisor.start()
    await asyncio.sleep(0.05)
    snapshot = supervisor.snapshot()
    await supervisor.stop()

    assert starts == 2
    assert snapshot["failing"]["restarts"] == 1
    assert snapshot["failing"]["done"] is True