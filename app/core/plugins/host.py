import logging
from typing import Dict, List, Optional, Any, TypeVar, Type
from app.core.plugins.models import Capability
from app.core.plugins.contract import PluginContract

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CapabilityRegistry:
    """Authority for discovery of services provided by plugins."""

    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}
        self._providers: Dict[str, PluginContract] = {}

    def register(self, capability: Capability, provider: PluginContract):
        """Register a service capability and its provider."""
        self._capabilities[capability.name] = capability
        self._providers[capability.name] = provider
        logger.info(f"[host] Registered capability: {capability.name} from {provider.manifest.plugin_id}")

    def resolve(self, capability_name: str) -> Optional[PluginContract]:
        """Resolve a capability name to its providing plugin."""
        return self._providers.get(capability_name)

    def list_capabilities(self) -> List[Capability]:
        """List all registered capabilities."""
        return list(self._capabilities.values())

class ExtensionHost:
    """The runtime environment provided to plugins for interacting with the platform."""

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry

    def get_service(self, service_name: str) -> Optional[Any]:
        """Discovery hook for plugins to find services/capabilities."""
        provider = self.capabilities.resolve(service_name)
        if provider:
            # In a real implementation, we would return a specific interface object
            return provider
        return None

    def emit_event(self, event_name: str, payload: Dict[str, Any]):
        """Publish events to the platform Event Bus."""
        # Future: Integrate with app.core.event_bus
        logger.debug(f"[host] Event emitted: {event_name}")

    def log(self, level: str, message: str):
        """Standardized logging for plugins."""
        # Future: Scope log messages to the plugin ID
        logger.info(f"[plugin-log] {message}")
