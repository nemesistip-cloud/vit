import logging
import asyncio
import time
from typing import Dict, List, Optional, Type, Any
from app.core.registry.models import ModuleMetadata, ModuleRuntimeInfo, ModuleStatus, HealthStatus
from app.core.registry.contract import ModuleContract
from app.core.registry.validator import DependencyValidator

logger = logging.getLogger(__name__)

class ModuleRegistry:
    """The authoritative source of truth for all runtime modules and service discovery."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModuleRegistry, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._modules: Dict[str, ModuleContract] = {}
        self._runtime_info: Dict[str, ModuleRuntimeInfo] = {}
        self._lock = asyncio.Lock()

    async def register(self, module: ModuleContract):
        """Register a module instance and validate its contract."""
        metadata = module.metadata
        module_id = metadata.module_id

        async with self._lock:
            if module_id in self._modules:
                # Same instance → idempotent no-op
                if self._modules[module_id] is module:
                    return
                # Different instance with same ID → programming error
                raise ValueError(
                    f"Module duplication detected: '{module_id}' is already registered "
                    f"with a different instance. Use a unique module_id."
                )

            logger.info(f"[registry] Registering module: {module_id} v{metadata.version}")

            # Create runtime info
            self._runtime_info[module_id] = ModuleRuntimeInfo(
                metadata=metadata,
                status=ModuleStatus.REGISTERED,
                health=HealthStatus.UNKNOWN,
                uptime_start=time.time()
            )
            self._modules[module_id] = module

    def validate_dependencies(self):
        """Invoke the dependency validator on the current module set."""
        validator = DependencyValidator(self._modules)
        validator.validate_all()

    def get_init_order(self) -> List[ModuleRuntimeInfo]:
        """Return modules in correct initialization order based on dependencies."""
        validator = DependencyValidator(self._modules)
        order = validator._topological_sort()
        return [self._runtime_info[mid] for mid in order if mid in self._runtime_info]

    def get_module(self, module_id: str) -> Optional[ModuleContract]:
        """Lookup a module by its unique ID."""
        return self._modules.get(module_id)

    def get_runtime_info(self, module_id: str) -> Optional[ModuleRuntimeInfo]:
        """Get runtime state and health for a specific module."""
        return self._runtime_info.get(module_id)

    def list_modules(self) -> List[str]:
        """List all registered module IDs."""
        return list(self._modules.keys())

    def clear(self):
        """Reset registry state for testing or re-initialization."""
        self._modules.clear()
        self._runtime_info.clear()

    # --- Service Discovery ---

    def discover_by_capability(self, capability: str) -> List[ModuleContract]:
        """Find all modules providing a specific capability."""
        matches = []
        for mid, info in self._runtime_info.items():
            if capability in info.metadata.capabilities:
                matches.append(self._modules[mid])
        return matches

    def discover_by_domain(self, domain: str) -> List[ModuleContract]:
        """Find all modules within a specific domain."""
        matches = []
        for mid, info in self._runtime_info.items():
            if info.metadata.domain == domain:
                matches.append(self._modules[mid])
        return matches

    # --- Runtime State Management ---

    async def update_status(self, module_id: str, status: ModuleStatus):
        """Update the lifecycle state of a module."""
        if module_id in self._runtime_info:
            self._runtime_info[module_id].status = status
            logger.debug(f"[registry] Module {module_id} status changed to {status.value}")

    async def update_health(self, module_id: str, health: HealthStatus):
        """Update the health status of a module."""
        if module_id in self._runtime_info:
            info = self._runtime_info[module_id]
            info.health = health
            info.last_health_check = time.time()

    async def report_error(self, module_id: str):
        """Increment error count for a module."""
        if module_id in self._runtime_info:
            self._runtime_info[module_id].error_count += 1

    # --- Diagnostics ---

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return a snapshot of the entire registry state."""
        return {
            "module_count": len(self._modules),
            "modules": {mid: info.dict() for mid, info in self._runtime_info.items()},
            "discovery_stats": {
                "domains": list(set(info.metadata.domain for info in self._runtime_info.values())),
                "capabilities": list(set(cap for info in self._runtime_info.values() for cap in info.metadata.capabilities))
            }
        }

# Global Registry Singleton
registry = ModuleRegistry()
