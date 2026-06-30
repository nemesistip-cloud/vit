import asyncio
import logging
import signal
import time
import os
from enum import Enum
from typing import Dict, List, Optional, Type, Any, Set

from app.core.registry.manager import registry
from app.core.registry.models import ModuleStatus, HealthStatus, ModuleMetadata
from app.core.registry.contract import ModuleContract

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
    domain: str = "Core"
    owner: str = "Core Team"

    def __init__(self, kernel: 'VITRuntimeKernel'):
        self.kernel = kernel
        self._metadata = ModuleMetadata(
            module_id=self.name,
            name=self.name.replace("_", " ").title(),
            owner=self.owner,
            domain=self.domain,
            dependencies=self.dependencies
        )

    @property
    def metadata(self) -> ModuleMetadata:
        return self._metadata

    async def initialize(self, config: Dict[str, Any]):
        await registry.update_status(self.name, ModuleStatus.INITIALIZING)
        await self._on_initialize(config)
        await registry.update_status(self.name, ModuleStatus.INITIALIZED)

    async def start(self):
        logger.info(f"[kernel] Starting subsystem: {self.name}")
        await registry.update_status(self.name, ModuleStatus.STARTING)
        await self._on_start()
        await registry.update_status(self.name, ModuleStatus.STARTED)
        await registry.update_status(self.name, ModuleStatus.READY)

    async def stop(self):
        logger.info(f"[kernel] Stopping subsystem: {self.name}")
        await registry.update_status(self.name, ModuleStatus.STOPPING)
        await self._on_stop()
        await registry.update_status(self.name, ModuleStatus.STOPPED)

    async def check_health(self) -> HealthStatus:
        return HealthStatus.HEALTHY

    async def get_diagnostics(self) -> Dict[str, Any]:
        return {}

    async def _on_initialize(self, config: Dict[str, Any]):
        pass

    async def _on_start(self):
        pass

    async def _on_stop(self):
        pass

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
        self.startup_time = time.time()
        self.config: Dict[str, Any] = {}
        self._health_loop_task: Optional[asyncio.Task] = None

    async def register_subsystem(self, subsystem_class: Type[Subsystem]):
        """Register a subsystem with the kernel and registry."""
        sub = subsystem_class(self)
        await registry.register(sub)
        logger.debug(f"[kernel] Registered subsystem: {sub.name}")

    async def boot(self):
        """Deterministic startup of all registered subsystems via the registry."""
        if self.state != KernelState.INITIALIZING:
            logger.warning(f"[kernel] Kernel already in {self.state.value} state.")
            return

        logger.info("[kernel] VIT Runtime Kernel booting...")
        self.state = KernelState.STARTING

        # 1. Resolve startup order from registry
        try:
            registry.validate_dependencies()
            module_ids = registry.list_modules()
            ordered_ids = self._resolve_dependencies(module_ids)
        except Exception as e:
            logger.critical(f"[kernel] Boot validation failed: {e}")
            self.state = KernelState.STOPPED
            raise

        # 2. Sequential Startup
        for mid in ordered_ids:
            sub = registry.get_module(mid)
            try:
                start_ts = time.time()
                await sub.initialize(self.config)
                await sub.start()
                logger.info(f"[kernel] Subsystem {mid} started in {time.time() - start_ts:.3f}s")
            except Exception as e:
                logger.error(f"[kernel] Critical failure starting {mid}: {e}", exc_info=True)
                self.state = KernelState.DEGRADED
                if mid in ["config", "database", "redis"]:
                    logger.critical(f"[kernel] Foundational subsystem {mid} failed. Halting.")
                    await self.shutdown()
                    raise

        if self.state != KernelState.DEGRADED:
            self.state = KernelState.RUNNING

        self._health_loop_task = asyncio.create_task(self._health_supervision_loop())
        logger.info(f"[kernel] VIT Runtime Kernel RUNNING (boot time: {time.time() - self.startup_time:.2f}s)")

    async def shutdown(self):
        """Graceful shutdown of all subsystems in reverse order."""
        if self.state in [KernelState.SHUTTING_DOWN, KernelState.STOPPED]:
            return

        logger.info("[kernel] VIT Runtime Kernel shutting down...")
        self.state = KernelState.SHUTTING_DOWN

        if self._health_loop_task:
            self._health_loop_task.cancel()

        module_ids = registry.list_modules()
        try:
            ordered_ids = self._resolve_dependencies(module_ids)
            for mid in reversed(ordered_ids):
                sub = registry.get_module(mid)
                try:
                    await sub.stop()
                except Exception as e:
                    logger.error(f"[kernel] Error stopping {mid}: {e}")
        except Exception:
            for mid in reversed(module_ids):
                sub = registry.get_module(mid)
                try:
                    await sub.stop()
                except Exception:
                    pass

        self.state = KernelState.STOPPED
        logger.info("[kernel] VIT Runtime Kernel STOPPED.")

    def _resolve_dependencies(self, module_ids: List[str]) -> List[str]:
        """Dependency resolution for a list of modules."""
        visited = set()
        stack = []
        path = set()

        def visit(mid):
            if mid in path:
                raise Exception(f"Circular dependency detected at {mid}")
            if mid in visited:
                return

            sub = registry.get_module(mid)
            if not sub:
                raise Exception(f"Module {mid} not found in registry.")

            path.add(mid)
            for dep in sub.metadata.dependencies:
                visit(dep)
            path.remove(mid)

            visited.add(mid)
            stack.append(mid)

        for mid in module_ids:
            visit(mid)
        return stack

    async def _health_supervision_loop(self):
        """Supervise subsystem health via registry."""
        while self.state in [KernelState.RUNNING, KernelState.DEGRADED]:
            try:
                all_healthy = True
                for mid in registry.list_modules():
                    sub = registry.get_module(mid)
                    try:
                        h = await sub.check_health()
                        await registry.update_health(mid, h)
                        if h != HealthStatus.HEALTHY:
                            all_healthy = False
                    except Exception as e:
                        logger.error(f"[kernel] Health check failed for {mid}: {e}")
                        await registry.report_error(mid)
                        all_healthy = False

                self.state = KernelState.RUNNING if all_healthy else KernelState.DEGRADED
            except Exception as e:
                logger.error(f"[kernel] Global health supervision error: {e}")

            await asyncio.sleep(30)

    def get_status(self) -> Dict[str, Any]:
        """Diagnostic snapshot from kernel and registry."""
        return {
            "kernel_state": self.state.value,
            "uptime_seconds": round(time.time() - self.startup_time, 2),
            "registry": registry.get_diagnostics()
        }

kernel = VITRuntimeKernel()

def setup_signal_handlers():
    """Setup OS signal handlers for graceful kernel shutdown."""
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(kernel.shutdown()))
        except NotImplementedError:
            pass
