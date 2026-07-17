from abc import abstractmethod
from typing import Any, Dict, List, Optional
from app.core.registry.contract import ModuleContract
from app.core.plugins.models import PluginManifest, PluginStatus

class PluginContract(ModuleContract):
    """Extended contract for all VIT Plugins."""

    @property
    @abstractmethod
    def manifest(self) -> PluginManifest:
        """Return the plugin's manifest."""
        pass

    @abstractmethod
    async def activate(self):
        """Lifecycle hook for plugin activation."""
        pass

    @abstractmethod
    async def suspend(self):
        """Lifecycle hook to temporarily suspend plugin execution."""
        pass

    @abstractmethod
    async def resume(self):
        """Lifecycle hook to resume plugin execution from suspension."""
        pass

    @abstractmethod
    async def upgrade(self, new_version: str, config: Dict[str, Any]):
        """Lifecycle hook for plugin version migration."""
        pass

    # Compatibility with ModuleContract
    async def initialize(self, config: Dict[str, Any]):
        """Default initializer delegating to hook if present."""
        if hasattr(self, '_on_initialize'):
            await self._on_initialize(config)

    async def start(self):
        """Default start hook delegating to hook if present."""
        if hasattr(self, '_on_start'):
            await self._on_start()

    async def stop(self):
        """Default stop hook delegating to hook if present."""
        if hasattr(self, '_on_stop'):
            await self._on_stop()

    async def check_health(self):
        """Default health check delegating to health_check or returning healthy."""
        from app.core.registry.models import HealthStatus
        is_healthy = True
        if hasattr(self, 'health_check'):
            is_healthy = await self.health_check()
        elif hasattr(self, '_on_health_check'):
            is_healthy = await self._on_health_check()
        return HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY

    async def get_diagnostics(self) -> Dict[str, Any]:
        """Default diagnostics returning basic status."""
        if hasattr(self, '_on_get_diagnostics'):
            return await self._on_get_diagnostics()
        return {
            "status": getattr(self, "state", "unknown")
        }

    @property
    def metadata(self):
        # Bridge PluginManifest to ModuleMetadata if needed,
        # but the PluginFramework will handle registration.
        from app.core.registry.models import ModuleMetadata
        m = self.manifest
        return ModuleMetadata(
            module_id=m.plugin_id,
            name=m.name,
            version=m.version,
            description=m.description,
            owner=m.author,
            domain="plugin",
            dependencies=list(m.dependencies.keys()),
            optional_dependencies=list(m.optional_dependencies.keys()),
            capabilities=m.capabilities,
            config_schema=m.config_schema,
            published_events=m.published_events,
            consumed_events=m.consumed_events
        )
