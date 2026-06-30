import asyncio
import logging
import signal
import time
import os
from enum import Enum
from typing import Dict, List, Optional, Type, Any, Set

logger = logging.getLogger(__name__)

class KernelState(Enum):
    INITIALIZING = "INITIALIZING"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    STOPPED = "STOPPED"

class Subsystem:
    """Base class for all VIT Kernel Subsystems."""
    name: str = "base_subsystem"
    dependencies: List[str] = []

    def __init__(self, kernel: 'VITRuntimeKernel'):
        self.kernel = kernel
        self.state = KernelState.STOPPED
        self.last_health_check = time.time()
        self.error_count = 0

    async def start(self):
        """Initialize and start the subsystem."""
        logger.info(f"[kernel] Starting subsystem: {self.name}")
        self.state = KernelState.STARTING
        await self._on_start()
        self.state = KernelState.RUNNING

    async def stop(self):
        """Gracefully stop the subsystem."""
        logger.info(f"[kernel] Stopping subsystem: {self.name}")
        self.state = KernelState.SHUTTING_DOWN
        await self._on_stop()
        self.state = KernelState.STOPPED

    async def _on_start(self):
        """Subsystem specific startup logic."""
        pass

    async def _on_stop(self):
        """Subsystem specific shutdown logic."""
        pass

    async def health_check(self) -> bool:
        """Return True if the subsystem is healthy."""
        self.last_health_check = time.time()
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
        """Register a subsystem with the kernel."""
        sub = subsystem_class(self)
        if sub.name in self.subsystems:
            logger.warning(f"[kernel] Subsystem {sub.name} already registered.")
            return
        self.subsystems[sub.name] = sub
        logger.debug(f"[kernel] Registered subsystem: {sub.name} (deps: {sub.dependencies})")

    async def boot(self):
        """Deterministic startup of all registered subsystems."""
        if self.state != KernelState.INITIALIZING:
            logger.warning(f"[kernel] Kernel already in {self.state.value} state.")
            return

        logger.info("[kernel] VIT Runtime Kernel booting...")
        self.state = KernelState.STARTING

        # 1. Resolve startup order
        try:
            ordered_subsystems = self._resolve_dependencies()
        except Exception as e:
            logger.critical(f"[kernel] Dependency resolution failed: {e}")
            self.state = KernelState.STOPPED
            raise

        # 2. Sequential Startup
        for sub_name in ordered_subsystems:
            sub = self.subsystems[sub_name]
            try:
                start_ts = time.time()
                await sub.start()
                logger.info(f"[kernel] Subsystem {sub_name} started in {time.time() - start_ts:.3f}s")
            except Exception as e:
                logger.error(f"[kernel] Critical failure starting {sub_name}: {e}", exc_info=True)
                self.state = KernelState.DEGRADED
                # Decision: In production we may want to stop booting if a critical dependency fails
                if sub_name in ["database", "redis", "config"]:
                    logger.critical(f"[kernel] Foundational subsystem {sub_name} failed. Halting.")
                    await self.shutdown()
                    raise

        if self.state != KernelState.DEGRADED:
            self.state = KernelState.RUNNING

        # 3. Start Health Supervision
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

        # Stop in reverse order of startup
        try:
            ordered_subsystems = self._resolve_dependencies()
            for sub_name in reversed(ordered_subsystems):
                sub = self.subsystems[sub_name]
                try:
                    await sub.stop()
                except Exception as e:
                    logger.error(f"[kernel] Error stopping {sub_name}: {e}")
        except Exception:
            # Fallback if dependency resolution fails during shutdown
            for sub in reversed(list(self.subsystems.values())):
                try:
                    await sub.stop()
                except Exception:
                    pass

        self.state = KernelState.STOPPED
        logger.info("[kernel] VIT Runtime Kernel STOPPED.")

    def _resolve_dependencies(self) -> List[str]:
        """Simple topological sort for subsystem dependencies."""
        visited = set()
        stack = []
        path = set()

        def visit(name):
            if name in path:
                raise Exception(f"Circular dependency detected at {name}")
            if name in visited:
                return

            sub = self.subsystems.get(name)
            if not sub:
                raise Exception(f"Subsystem {name} not found but listed as a dependency.")

            path.add(name)
            for dep in sub.dependencies:
                visit(dep)
            path.remove(name)

            visited.add(name)
            stack.append(name)

        for name in self.subsystems:
            visit(name)
        return stack

    async def _health_supervision_loop(self):
        """Supervise subsystem health and update kernel state."""
        while self.state == KernelState.RUNNING or self.state == KernelState.DEGRADED:
            try:
                all_healthy = True
                for name, sub in self.subsystems.items():
                    try:
                        is_healthy = await sub.health_check()
                        if not is_healthy:
                            logger.warning(f"[kernel] Subsystem {name} reported unhealthy.")
                            all_healthy = False
                    except Exception as e:
                        logger.error(f"[kernel] Health check failed for {name}: {e}")
                        sub.error_count += 1
                        all_healthy = False

                self.state = KernelState.RUNNING if all_healthy else KernelState.DEGRADED
            except Exception as e:
                logger.error(f"[kernel] Global health supervision error: {e}")

            await asyncio.sleep(30)

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic information about the kernel and subsystems."""
        return {
            "kernel_state": self.state.value,
            "uptime_seconds": round(time.time() - self.startup_time, 2),
            "subsystem_count": len(self.subsystems),
            "subsystems": {
                name: {
                    "state": sub.state.value,
                    "last_check_delta": round(time.time() - sub.last_health_check, 2),
                    "error_count": sub.error_count
                } for name, sub in self.subsystems.items()
            }
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
