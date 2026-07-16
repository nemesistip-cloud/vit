import asyncio
import logging
from app.core.kernel import VITRuntimeKernel, Subsystem
from app.core.registry.manager import registry

async def test_boot_sequence():
    kernel = VITRuntimeKernel()

    class MockSub(Subsystem):
        name = "mock_sub"
        async def _on_start(self):
            print("MockSub Started")

    kernel.register_subsystem(MockSub)
    print(f"Subsystems in kernel: {list(kernel.subsystems.keys())}")
    print(f"Modules in registry before boot: {len(registry.list_modules())}")

    await kernel.boot()

    print(f"Modules in registry after boot: {len(registry.list_modules())}")
    print(f"Kernel state: {kernel.state}")

    if len(registry.list_modules()) > 0:
        print("SUCCESS: Subsystems correctly registered during boot.")
    else:
        print("FAILURE: Subsystems missing from registry.")

if __name__ == "__main__":
    asyncio.run(test_boot_sequence())
