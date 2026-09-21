from abc import ABC, abstractmethod
from typing import Any, Dict
from app.core.registry.models import ModuleMetadata, HealthStatus

class ModuleContract(ABC):
    """Authoritative contract for all VIT Ecosystem modules."""

    @property
    @abstractmethod
    def metadata(self) -> ModuleMetadata:
        """Return the module's registration metadata."""
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]):
        """Bootstrapping logic for the module."""
        pass

    @abstractmethod
    async def start(self):
        """Lifecycle hook to start module execution."""
        pass

    @abstractmethod
    async def stop(self):
        """Lifecycle hook for graceful shutdown."""
        pass

    @abstractmethod
    async def check_health(self) -> HealthStatus:
        """Return the current health status of the module."""
        pass

    @abstractmethod
    async def get_diagnostics(self) -> Dict[str, Any]:
        """Return runtime diagnostics for the module."""
        pass
