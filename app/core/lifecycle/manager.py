import logging
import asyncio
import time
from typing import Dict, List, Set, Any, Optional
from app.core.registry.manager import registry
from app.core.registry.models import ModuleStatus, HealthStatus, LifecycleDiagnostic
from app.core.lifecycle.state_machine import LifecycleStateMachine
from app.core.lifecycle.orchestrator import DependencyOrchestrator
from app.core.lifecycle.recovery import RecoveryManager

logger = logging.getLogger(__name__)

class LifecycleManager:
    """The authoritative runtime component responsible for managing module lifecycles."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LifecycleManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.state_machines: Dict[str, LifecycleStateMachine] = {}
        self.diagnostics: Dict[str, LifecycleDiagnostic] = {}
        self.recovery = RecoveryManager()
        self._boot_lock = asyncio.Lock()
        self.startup_timeline: List[Dict[str, Any]] = []

    async def initialize_modules(self, config: Dict[str, Any]):
        """Coordinate parallel initialization of all registered modules."""
        async with self._boot_lock:
            logger.info("[lifecycle] Initializing module ecosystem...")
            orchestrator = DependencyOrchestrator(registry._modules)
            plan = orchestrator.get_execution_plan()

            for level_idx, level in enumerate(plan):
                logger.info(f"[lifecycle] Initializing Layer {level_idx}: {level}")
                tasks = [self._initialize_module(mid, config) for mid in level]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for mid, res in zip(level, results):
                    if isinstance(res, Exception):
                        logger.error(f"[lifecycle] Layer {level_idx} failed at {mid}: {res}")
                        # If a critical module fails, we might want to stop, but for now we continue
                        # and mark it as FAILED.

    async def start_modules(self):
        """Coordinate parallel startup of all initialized modules."""
        logger.info("[lifecycle] Starting module ecosystem...")
        orchestrator = DependencyOrchestrator(registry._modules)
        plan = orchestrator.get_execution_plan()

        for level_idx, level in enumerate(plan):
            logger.info(f"[lifecycle] Starting Layer {level_idx}: {level}")
            tasks = [self._start_module(mid) for mid in level]
            results = await asyncio.gather(*tasks, return_exceptions=True)

    async def stop_modules(self):
        """Coordinate reverse-order shutdown of all modules."""
        logger.info("[lifecycle] Stopping module ecosystem...")
        orchestrator = DependencyOrchestrator(registry._modules)
        order = orchestrator.get_sequential_order()

        # Stop in reverse topological order
        for mid in reversed(order):
            await self._stop_module(mid)

    # --- Private Module Operations ---

    async def _initialize_module(self, module_id: str, config: Dict[str, Any]):
        module = registry.get_module(module_id)
        if not module:
            return

        sm = self._get_or_create_sm(module_id)
        if not sm.transition_to(ModuleStatus.INITIALIZING):
            return

        start_ts = time.time()
        try:
            await self.recovery.execute_with_recovery(
                module_id, module.initialize, config.get(module_id, {})
            )
            sm.transition_to(ModuleStatus.INITIALIZED)
            await registry.update_status(module_id, ModuleStatus.INITIALIZED)

            diag = self._get_or_create_diag(module_id)
            diag.boot_time_ms += (time.time() - start_ts) * 1000
        except Exception as e:
            logger.error(f"[lifecycle] Failed to initialize {module_id}: {e}")
            sm.transition_to(ModuleStatus.FAILED)
            await registry.update_status(module_id, ModuleStatus.FAILED)
            self._report_failure(module_id, "initialization", str(e))

    async def _start_module(self, module_id: str):
        module = registry.get_module(module_id)
        sm = self._get_or_create_sm(module_id)

        if not sm.can_transition_to(ModuleStatus.STARTING):
            logger.warning(f"[lifecycle] Cannot start {module_id} from {sm.current_state.value}")
            return

        sm.transition_to(ModuleStatus.STARTING)
        await registry.update_status(module_id, ModuleStatus.STARTING)

        start_ts = time.time()
        try:
            await self.recovery.execute_with_recovery(module_id, module.start)
            sm.transition_to(ModuleStatus.RUNNING)
            await registry.update_status(module_id, ModuleStatus.RUNNING)

            # Final transition to READY if health check passes
            health = await module.check_health()
            if health == HealthStatus.HEALTHY:
                sm.transition_to(ModuleStatus.READY)
                await registry.update_status(module_id, ModuleStatus.READY)

            diag = self._get_or_create_diag(module_id)
            diag.boot_time_ms += (time.time() - start_ts) * 1000

            self.startup_timeline.append({
                "module_id": module_id,
                "start_time": start_ts,
                "duration_ms": (time.time() - start_ts) * 1000
            })
        except Exception as e:
            logger.error(f"[lifecycle] Failed to start {module_id}: {e}")
            sm.transition_to(ModuleStatus.FAILED)
            await registry.update_status(module_id, ModuleStatus.FAILED)
            self._report_failure(module_id, "startup", str(e))

    async def _stop_module(self, module_id: str):
        module = registry.get_module(module_id)
        sm = self._get_or_create_sm(module_id)

        if not sm.transition_to(ModuleStatus.STOPPING):
            return

        await registry.update_status(module_id, ModuleStatus.STOPPING)
        try:
            await module.stop()
            sm.transition_to(ModuleStatus.STOPPED)
            await registry.update_status(module_id, ModuleStatus.STOPPED)
            sm.transition_to(ModuleStatus.SHUTDOWN)
            await registry.update_status(module_id, ModuleStatus.SHUTDOWN)
        except Exception as e:
            logger.error(f"[lifecycle] Error stopping {module_id}: {e}")
            sm.transition_to(ModuleStatus.FAILED)
            await registry.update_status(module_id, ModuleStatus.FAILED)

    # --- Helpers ---

    def _get_or_create_sm(self, module_id: str) -> LifecycleStateMachine:
        if module_id not in self.state_machines:
            self.state_machines[module_id] = LifecycleStateMachine(module_id)
        return self.state_machines[module_id]

    def _get_or_create_diag(self, module_id: str) -> LifecycleDiagnostic:
        if module_id not in self.diagnostics:
            self.diagnostics[module_id] = LifecycleDiagnostic(module_id=module_id)
        return self.diagnostics[module_id]

    def _report_failure(self, module_id: str, phase: str, error: str):
        diag = self._get_or_create_diag(module_id)
        diag.last_error = error
        diag.failure_reports.append({
            "phase": phase,
            "error": error,
            "timestamp": time.time()
        })

    def get_runtime_diagnostics(self) -> Dict[str, Any]:
        return {
            "startup_timeline": self.startup_timeline,
            "modules": {mid: diag.dict() for mid, diag in self.diagnostics.items()},
            "recovery_stats": self.recovery.get_stats()
        }

# Global Lifecycle Manager Singleton
lifecycle_manager = LifecycleManager()
