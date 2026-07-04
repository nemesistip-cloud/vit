import sys
import os
from unittest.mock import MagicMock

# Mock enough to import kernel
sys.modules['app.core.registry.manager'] = MagicMock()
sys.modules['app.core.lifecycle.manager'] = MagicMock()
sys.modules['app.core.observability.manager'] = MagicMock()
sys.modules['app.core.observability.models'] = MagicMock()

from app.core.kernel import VITRuntimeKernel, Subsystem

def run_verify():
    k = VITRuntimeKernel()
    # Check if get_subsystem is present
    if not hasattr(k, 'get_subsystem'):
        print("FAIL: get_subsystem missing")
        return

    class MockSub(Subsystem):
        name = "test_bc"

    k.subsystems["test_bc"] = MockSub(k)
    retrieved = k.get_subsystem("test_bc")
    if retrieved and retrieved.name == "test_bc":
        print("SUCCESS: get_subsystem functional")
    else:
        print("FAIL: get_subsystem failed to retrieve")

if __name__ == "__main__":
    run_verify()
