import pytest
import asyncio
from app.core.registry.manager import ModuleRegistry
from app.core.registry.models import ModuleMetadata, ModuleStatus, HealthStatus
from app.core.registry.contract import ModuleContract
from app.core.lifecycle.state_machine import LifecycleStateMachine
from app.core.lifecycle.orchestrator import DependencyOrchestrator
from app.core.lifecycle.manager import LifecycleManager

class MockModule(ModuleContract):
    def __init__(self, mid, deps=[], fail_start=False):
        self._metadata = ModuleMetadata(
            module_id=mid,
            name=mid,
            owner="test",
            domain="test",
            dependencies=deps
        )
        self.initialized = False
        self.started = False
        self.fail_start = fail_start

    @property
    def metadata(self): return self._metadata
    async def initialize(self, config): self.initialized = True
    async def start(self):
        if self.fail_start: raise Exception("Injected startup failure")
        self.started = True
    async def stop(self): self.started = False
    async def check_health(self): return HealthStatus.HEALTHY
    async def get_diagnostics(self): return {}

@pytest.mark.asyncio
async def test_state_machine_transitions():
    sm = LifecycleStateMachine("test_mod")
    assert sm.current_state == ModuleStatus.REGISTERED
    assert sm.transition_to(ModuleStatus.VALIDATED) is True
    assert sm.transition_to(ModuleStatus.INITIALIZING) is True
    assert sm.transition_to(ModuleStatus.FAILED) is True
    assert sm.transition_to(ModuleStatus.READY) is False

@pytest.mark.asyncio
async def test_orchestrator_parallel_plan():
    modules = {
        "m1": MockModule("m1"),
        "m2": MockModule("m2"),
        "m3": MockModule("m3", deps=["m1", "m2"]),
        "m4": MockModule("m4", deps=["m3"]),
        "m5": MockModule("m5", deps=["m1"])
    }
    orchestrator = DependencyOrchestrator(modules)
    plan = orchestrator.get_execution_plan()
    assert "m1" in plan[0]
    assert "m2" in plan[0]
    assert "m3" in plan[1]
    assert "m5" in plan[1]
    assert "m4" in plan[2]

@pytest.mark.asyncio
async def test_lifecycle_manager_boot_sequence():
    reg = ModuleRegistry()
    reg._modules.clear()
    reg._runtime_info.clear()
    m1 = MockModule("db")
    m2 = MockModule("api", deps=["db"])
    await reg.register(m1)
    await reg.register(m2)
    lm = LifecycleManager()
    lm.state_machines.clear()
    lm.diagnostics.clear()
    await lm.initialize_modules({})
    await lm.start_modules()
    assert m1.started is True
    assert m2.started is True
    assert lm.state_machines["db"].current_state == ModuleStatus.READY

@pytest.mark.asyncio
async def test_recovery_retry():
    reg = ModuleRegistry()
    reg._modules.clear()
    class Flaky(MockModule):
        def __init__(self, mid):
            super().__init__(mid)
            self.attempts = 0
        async def start(self):
            self.attempts += 1
            if self.attempts < 2: raise Exception("Transient")
            self.started = True
    m = Flaky("flaky")
    await reg.register(m)
    lm = LifecycleManager()
    lm.state_machines.clear()
    await lm.initialize_modules({})
    await lm.start_modules()
    assert m.attempts == 2
    assert m.started is True
