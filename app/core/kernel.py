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
        if await self.health_check():
            return HealthStatus.HEALTHY
        return HealthStatus.UNHEALTHY

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
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
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

        # Bridge to Module Registry
        # Note: registry.register is async, but we are in a sync method.
        # Subsystems are registered before boot.
        asyncio.get_event_loop().create_task(registry.register(sub))
        logger.debug(f"[kernel] Registered subsystem: {sub.name} (deps: {sub.dependencies})")

    async def boot(self):
        """Authoritative boot sequence delegating to LifecycleManager."""
        if self.state != KernelState.INITIALIZING:
            logger.warning(f"[kernel] Kernel already in {self.state.value} state.")
            return

        logger.info("[kernel] VIT Runtime Kernel booting...")
        self.state = KernelState.STARTING

        # 1. Initialize all modules
        await lifecycle_manager.initialize_modules(self.config)

        # 2. Start all modules
        await lifecycle_manager.start_modules()

        self.state = KernelState.RUNNING

        # 3. Start Health Supervision
        self._health_loop_task = asyncio.create_task(self._health_supervision_loop())

        logger.info(f"[kernel] VIT Runtime Kernel RUNNING (boot time: {time.time() - self.startup_time:.2f}s)")

    async def shutdown(self):
        """Graceful shutdown delegating to LifecycleManager."""
        if self.state in [KernelState.SHUTTING_DOWN, KernelState.STOPPED]:
            return

        logger.info("[kernel] VIT Runtime Kernel shutting down...")
        self.state = KernelState.SHUTTING_DOWN

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
                # In Track-003 we rely on ModuleRegistry for health status updates
                # but we could also trigger explicit checks here.
                pass
            except Exception as e:
                logger.error(f"[kernel] Global health supervision error: {e}")

            await asyncio.sleep(30)

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
