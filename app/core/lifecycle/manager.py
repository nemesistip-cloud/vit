import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from app.core.registry.manager import registry
from app.core.registry.models import ModuleStatus, LifecycleEvent, LifecycleDiagnostic
from app.core.observability.manager import obs_manager
from app.core.observability.models import MetricType, AlertSeverity

logger = logging.getLogger(__name__)

class LifecycleManager:
    """Manages the initialization and startup sequence of all registered modules."""

    def __init__(self):
        self.diagnostics: Dict[str, LifecycleDiagnostic] = {}

    async def initialize_modules(self, config: Dict[str, Any]):
        """Initialize all modules in correct dependency order."""
        ordered_modules = registry.get_init_order()
        logger.info(f"[lifecycle] Initializing modules in order: {[m.metadata.module_id for m in ordered_modules]}")

        for mod_info in ordered_modules:
            mid = mod_info.metadata.module_id
            start_time = time.time()
            try:
                await registry.update_status(mid, ModuleStatus.INITIALIZING)
                await mod_info.module.initialize(config)
                await registry.update_status(mid, ModuleStatus.INITIALIZED)

                duration = (time.time() - start_time) * 1000
                obs_manager.record_metric(f"module_init_time_ms", duration, labels={"module": mid})

            except Exception as e:
                logger.error(f"[lifecycle] Failed to initialize {mid}: {e}")
                await registry.update_status(mid, ModuleStatus.FAILED)
                obs_manager.emit_alert(
                    severity=AlertSeverity.ERROR,
                    title="Module Initialization Failed",
                    description=f"Module {mid} failed to initialize: {str(e)}",
                    module_id=mid
                )
                raise

    async def start_modules(self):
        """Start all initialized modules."""
        ordered_modules = registry.get_init_order()
        for mod_info in ordered_modules:
            mid = mod_info.metadata.module_id
            start_time = time.time()
            try:
                await registry.update_status(mid, ModuleStatus.STARTING)
                await mod_info.module.start()
                await registry.update_status(mid, ModuleStatus.RUNNING)

                duration = (time.time() - start_time) * 1000
                obs_manager.record_metric(f"module_start_time_ms", duration, labels={"module": mid})

            except Exception as e:
                logger.error(f"[lifecycle] Failed to start {mid}: {e}")
                await registry.update_status(mid, ModuleStatus.FAILED)
                obs_manager.emit_alert(
                    severity=AlertSeverity.CRITICAL,
                    title="Module Startup Failed",
                    description=f"Module {mid} failed to start: {str(e)}",
                    module_id=mid
                )

    async def stop_modules(self):
        """Stop all running modules in reverse order."""
        ordered_modules = reversed(registry.get_init_order())
        for mod_info in ordered_modules:
            mid = mod_info.metadata.module_id
            try:
                await registry.update_status(mid, ModuleStatus.STOPPING)
                await mod_info.module.stop()
                await registry.update_status(mid, ModuleStatus.STOPPED)
            except Exception as e:
                logger.error(f"[lifecycle] Error stopping {mid}: {e}")

    def get_runtime_diagnostics(self) -> Dict[str, Any]:
        return {mid: diag.dict() for mid, diag in self.diagnostics.items()}

lifecycle_manager = LifecycleManager()
