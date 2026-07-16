import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Mock necessary modules
registry_mock = MagicMock()
registry_mock.register = AsyncMock()
sys.modules['app.core.registry.manager'] = MagicMock(registry=registry_mock)
sys.modules['app.core.registry.contract'] = MagicMock()
sys.modules['app.core.registry.models'] = MagicMock()
sys.modules['app.core.lifecycle.manager'] = MagicMock()
sys.modules['app.core.observability.manager'] = MagicMock()
sys.modules['app.core.observability.models'] = MagicMock()

from app.core.kernel import VITRuntimeKernel, Subsystem

async def test_kernel_fix():
    print(f"Testing VITRuntimeKernel")
    k = VITRuntimeKernel()

    # Simulate subsystem registration
    class MockSubsystem(Subsystem):
        name = "test_sub"

    k.register_subsystem(MockSubsystem)

    # Give the background task a moment to run or just check the internal dict
    sub = k.get_subsystem("test_sub")
    print(f"Retrieved subsystem: {sub.name if sub else 'None'}")

    if sub and sub.name == "test_sub":
        print("Verification successful.")
    else:
        print("Verification failed: Subsystem not found.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_kernel_fix())
