import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from app.core.registry.manager import registry
from app.core.registry.models import ModuleStatus, LifecycleEvent, LifecycleDiagnostic
from app.core.observability.manager import obs_manager
from app.core.observability.models import MetricType, AlertSeverity, HealthStatus as ObsHealthStatus

logger = logging.getLogger(__name__)

# Column widths for the startup log table
_COL_NAME   = 22
_COL_STATUS = 12
_COL_MS     = 12
_COL_ERR    = 40


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
        """Start all initialized modules.

        On failure: logs the full traceback, explicitly marks the subsystem
        UNHEALTHY in obs_manager (so it's never left UNKNOWN), and continues
        to the next subsystem so remaining modules can still start.  The
        health supervision loop in the kernel will roll the worst subsystem
        status up into the kernel's overall state.
        """
        ordered_modules = registry.get_init_order()

        # Accumulate per-module results for the structured startup log.
        _results: List[Dict[str, Any]] = []

        for mod_info in ordered_modules:
            mid = mod_info.metadata.module_id
            start_time = time.time()
            error_msg: Optional[str] = None

            try:
                await registry.update_status(mid, ModuleStatus.STARTING)
                await mod_info.module.start()
                await registry.update_status(mid, ModuleStatus.RUNNING)

                duration_ms = (time.time() - start_time) * 1000
                obs_manager.record_metric(f"module_start_time_ms", duration_ms, labels={"module": mid})
                status_label = "RUNNING"

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = str(e)
                status_label = "FAILED"

                # Log with full traceback so the root cause is never hidden.
                logger.error(
                    "[lifecycle] Failed to start %s: %s",
                    mid, e,
                    exc_info=True,
                )
                await registry.update_status(mid, ModuleStatus.FAILED)

                # Explicitly mark UNHEALTHY so obs_manager reflects real state
                # and the kernel's health supervision loop can roll it up.
                # Never leave a failed subsystem at UNKNOWN.
                obs_manager.health.update_status(
                    mid,
                    ObsHealthStatus.UNHEALTHY,
                    f"Startup failed: {error_msg}",
                )

                obs_manager.emit_alert(
                    severity=AlertSeverity.CRITICAL,
                    title="Module Startup Failed",
                    description=f"Module {mid} failed to start: {error_msg}",
                    module_id=mid,
                )
                # Do NOT re-raise: let remaining modules attempt to start.

            _results.append({
                "name": mid,
                "status": status_label,
                "ms": round(duration_ms, 1),
                "error": error_msg or "",
            })

        # ── Structured startup log table ─────────────────────────────────────
        sep = (
            f"+{'-' * (_COL_NAME + 2)}"
            f"+{'-' * (_COL_STATUS + 2)}"
            f"+{'-' * (_COL_MS + 2)}"
            f"+{'-' * (_COL_ERR + 2)}+"
        )
        header = (
            f"| {'Subsystem':<{_COL_NAME}} "
            f"| {'Status':<{_COL_STATUS}} "
            f"| {'Boot (ms)':<{_COL_MS}} "
            f"| {'Error':<{_COL_ERR}} |"
        )
        rows = [sep, header, sep]
        for r in _results:
            rows.append(
                f"| {r['name']:<{_COL_NAME}} "
                f"| {r['status']:<{_COL_STATUS}} "
                f"| {r['ms']:<{_COL_MS}} "
                f"| {r['error'][:_COL_ERR]:<{_COL_ERR}} |"
            )
        rows.append(sep)
        table = "\n".join(rows)
        logger.info("[lifecycle] Subsystem startup summary:\n%s", table)

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
