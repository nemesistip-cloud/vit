import pytest
import asyncio
from app.core.kernel import VITRuntimeKernel, KernelState

@pytest.mark.asyncio
async def test_kernel_shutdown_idempotency():
    k = VITRuntimeKernel()
    # Initial state should be INITIALIZING or STOPPED/RUNNING
    k.state = KernelState.RUNNING

    await k.shutdown()
    assert k.state == KernelState.STOPPED

    # Second shutdown call must no-op cleanly
    await k.shutdown()
    assert k.state == KernelState.STOPPED
