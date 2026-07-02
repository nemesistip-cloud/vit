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
