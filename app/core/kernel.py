import asyncio
import logging
import signal
import time
import os
from enum import Enum
from typing import Dict, List, Optional, Type, Any, Set
from app.core.registry.manager import registry
from app.core.registry.contract import ModuleContract
from app.core.registry.models import ModuleMetadata, HealthStatus, ModuleStatus
from app.core.lifecycle.manager import lifecycle_manager
from app.core.observability.manager import obs_manager
from app.core.observability.models import HealthStatus as ObsHealthStatus

logger = logging.getLogger(__name__)

class KernelState(Enum):
    INITIALIZING = "INITIALIZING"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    STOPPED = "STOPPED"

class Subsystem(ModuleContract):
    """Base class for all VIT Kernel Subsystems, implementing ModuleContract."""
    name: str = "base_subsystem"
    dependencies: List[str] = []

    def __init__(self, kernel: 'VITRuntimeKernel'):
        self.kernel = kernel
        self.state = ModuleStatus.STOPPED
        self.last_health_check = time.time()
        self.error_count = 0
        self._metadata = ModuleMetadata(
            module_id=self.name,
            name=self.name.replace("_", " ").title(),
            owner="core",
            domain="infrastructure",
            dependencies=self.dependencies
        )

    @property
    def metadata(self) -> ModuleMetadata:
        return self._metadata

    async def initialize(self, config: Dict[str, Any]):
        await self._on_initialize(config)

    async def start(self):
        await self._on_start()

    async def stop(self):
        await self._on_stop()

    async def check_health(self) -> HealthStatus:
        self.last_health_check = time.time()
        is_healthy = await self.health_check()

        # Report to Observability Platform
        obs_status = ObsHealthStatus.HEALTHY if is_healthy else ObsHealthStatus.UNHEALTHY
        obs_manager.health.update_status(self.name, obs_status)

        return HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY

    async def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "error_count": self.error_count,
            "last_check": self.last_health_check
        }

    # --- Hooks for Subsystems ---

    async def _on_initialize(self, config: Dict[str, Any]):
        pass

    async def _on_start(self):
        pass

    async def _on_stop(self):
        pass

    async def health_check(self) -> bool:
        return True

class VITRuntimeKernel:
    """The foundational execution layer of the VIT Ecosystem."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VITRuntimeKernel, cls).__new__(cls)
            cls._instance._initialized_kernel = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized_kernel', False):
            return
        self._initialized_kernel = True
        self.state = KernelState.INITIALIZING
        self.subsystems: Dict[str, Subsystem] = {}
        self.startup_time = time.time()
        self.config: Dict[str, Any] = {}
        self._health_loop_task: Optional[asyncio.Task] = None

    def register_subsystem(self, subsystem_class: Type[Subsystem]):
        """Register a subsystem with the kernel and module registry."""
        sub = subsystem_class(self)
        if sub.name in self.subsystems:
            logger.warning(f"[kernel] Subsystem {sub.name} already registered.")
            return
        self.subsystems[sub.name] = sub
        logger.debug(f"[kernel] Registered subsystem: {sub.name} (deps: {sub.dependencies})")

    async def boot(self):
        """Authoritative boot sequence delegating to LifecycleManager."""
        if self.state != KernelState.INITIALIZING:
            logger.warning(f"[kernel] Kernel already in {self.state.value} state.")
            return

        # Formalize registration in the Module Registry now that we have an event loop
        for sub in self.subsystems.values():
            await registry.register(sub)
        """Authoritative boot sequence delegating to LifecycleManager."""
        if self.state != KernelState.INITIALIZING:
            logger.warning(f"[kernel] Kernel already in {self.state.value} state.")
            return

        logger.info("[kernel] VIT Runtime Kernel booting...")
        self.state = KernelState.STARTING

        # Observability: Record start
        obs_manager.record_metric("kernel_boot_sequence_start", 1.0)

        # 0. Load authoritative configuration
        from app.core.config.manager import config_manager
        await config_manager.load()
        self.config = config_manager.config.dict()

        # 1. Initialize all modules
        await lifecycle_manager.initialize_modules(self.config)

        # 2. Start all modules
        await lifecycle_manager.start_modules()

        self.state = KernelState.RUNNING

        # Observability: Record boot time
        boot_time = time.time() - self.startup_time
        obs_manager.record_metric("kernel_uptime_seconds", boot_time)
        obs_manager.record_metric("kernel_boot_time_ms", boot_time * 1000)

        # 3. Start Health Supervision
        self._health_loop_task = asyncio.create_task(self._health_supervision_loop())

        logger.info(f"[kernel] VIT Runtime Kernel RUNNING (boot time: {boot_time:.2f}s)")

    async def shutdown(self):
        """Graceful shutdown delegating to LifecycleManager."""
        if self.state in [KernelState.SHUTTING_DOWN, KernelState.STOPPED]:
            return

        logger.info("[kernel] VIT Runtime Kernel shutting down...")
        self.state = KernelState.SHUTTING_DOWN

        obs_manager.record_metric("kernel_shutdown_start", 1.0)

        if self._health_loop_task:
            self._health_loop_task.cancel()

        # Shutdown all modules
        await lifecycle_manager.stop_modules()

        self.state = KernelState.STOPPED
        logger.info("[kernel] VIT Runtime Kernel STOPPED.")

    async def _health_supervision_loop(self):
        """Supervise ecosystem health."""
        while self.state == KernelState.RUNNING or self.state == KernelState.DEGRADED:
            try:
                # Trigger health checks for all subsystems
                for sub in self.subsystems.values():
                    await sub.check_health()

                # Check overall status
                obs_status = obs_manager.health.get_overall_status()
                if obs_status == ObsHealthStatus.UNHEALTHY:
                    if self.state != KernelState.DEGRADED:
                        logger.error("[kernel] SYSTEM DEGRADED: Unhealthy subsystems detected.")
                        self.state = KernelState.DEGRADED
                elif obs_status == ObsHealthStatus.HEALTHY:
                    if self.state == KernelState.DEGRADED:
                        logger.info("[kernel] SYSTEM RECOVERED: All subsystems healthy.")
                        self.state = KernelState.RUNNING

                # Record metrics
                obs_manager.record_metric("active_subsystems", len(self.subsystems))

            except Exception as e:
                logger.error(f"[kernel] Global health supervision error: {e}")

            await asyncio.sleep(30)

    def get_subsystem(self, name: str) -> Optional[Subsystem]:
        """Retrieve a registered subsystem by name."""
        return self.subsystems.get(name)

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic information about the kernel and lifecycle."""
        return {
            "kernel_state": self.state.value,
            "uptime_seconds": round(time.time() - self.startup_time, 2),
            "lifecycle": lifecycle_manager.get_runtime_diagnostics()
        }

# Global Kernel Instance
kernel = VITRuntimeKernel()

def setup_signal_handlers():
    """Setup OS signal handlers for graceful kernel shutdown."""
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(kernel.shutdown()))
        except NotImplementedError:
            # Windows fallback
            pass
