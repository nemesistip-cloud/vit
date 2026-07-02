import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from app.core.plugins.models import PluginManifest, PluginRuntimeInfo, PluginStatus, SecurityClassification
from app.core.plugins.contract import PluginContract
from app.core.plugins.discovery import PluginDiscovery
from app.core.plugins.validator import PluginValidator
from app.core.plugins.resolver import DependencyResolver
from app.core.plugins.loader import PluginLoader
from app.core.registry.manager import registry
from app.core.observability.manager import obs_manager

logger = logging.getLogger(__name__)

class PluginManager:
    """Orchestrates the entire plugin lifecycle."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.plugins: Dict[str, PluginContract] = {}
        self.runtime_info: Dict[str, PluginRuntimeInfo] = {}
        self._lock = asyncio.Lock()

        # Components
        self.discovery = PluginDiscovery(["app/plugins", "plugins"])
        self.validator = PluginValidator("1.0.0") # Use platform version
        self.loader = PluginLoader("app/plugins")

    async def bootstrap(self):
        """Initial discovery and loading sequence."""
        logger.info("[plugins] Starting Plugin Framework bootstrap...")

        # 1. Discover
        manifests = self.discovery.discover()

        # 2. Resolve Order
        resolver = DependencyResolver(manifests)
        try:
            load_order = resolver.resolve_order()
        except ValueError as e:
            logger.error(f"[plugins] Dependency resolution failed: {e}")
            return

        # 3. Load & Initialize
        for plugin_id in load_order:
            manifest = manifests[plugin_id]
            if self.validator.validate(manifest):
                await self.load_plugin(manifest)
            else:
                logger.error(f"[plugins] Validation failed for {plugin_id}")

    async def load_plugin(self, manifest: PluginManifest) -> bool:
        """Load, register and initialize a single plugin."""
        plugin_id = manifest.plugin_id
        async with self._lock:
            if plugin_id in self.plugins:
                return True

            logger.info(f"[plugins] Loading {plugin_id} v{manifest.version}...")

            # Update status
            self.runtime_info[plugin_id] = PluginRuntimeInfo(
                manifest=manifest,
                status=PluginStatus.INITIALIZING,
                load_time=time.time()
            )

            # Load
            instance = self.loader.load(manifest)
            if not instance:
                self.runtime_info[plugin_id].status = PluginStatus.FAILED
                return False

            self.plugins[plugin_id] = instance

            # Bridge to Core Registry
            await registry.register(instance)

            # Initialize
            try:
                await instance.initialize({}) # Config injection handled by Framework
                self.runtime_info[plugin_id].status = PluginStatus.INITIALIZED
                logger.info(f"[plugins] {plugin_id} initialized.")
                return True
            except Exception as e:
                logger.error(f"[plugins] Failed to initialize {plugin_id}: {e}")
                self.runtime_info[plugin_id].status = PluginStatus.FAILED
                return False

    async def activate_all(self):
        """Activate all initialized plugins."""
        for plugin_id, instance in self.plugins.items():
            if self.runtime_info[plugin_id].status == PluginStatus.INITIALIZED:
                try:
                    self.runtime_info[plugin_id].status = PluginStatus.ACTIVATING
                    await instance.activate()
                    await instance.start() # Ensure ModuleContract compatibility
                    self.runtime_info[plugin_id].status = PluginStatus.ACTIVE
                    logger.info(f"[plugins] {plugin_id} activated.")
                except Exception as e:
                    logger.error(f"[plugins] Activation failed for {plugin_id}: {e}")
                    self.runtime_info[plugin_id].status = PluginStatus.FAILED

    async def shutdown_all(self):
        """Gracefully stop all plugins."""
        for plugin_id in reversed(list(self.plugins.keys())):
            instance = self.plugins[plugin_id]
            logger.info(f"[plugins] Shutting down {plugin_id}...")
            try:
                self.runtime_info[plugin_id].status = PluginStatus.SHUTTING_DOWN
                await instance.stop()
                self.runtime_info[plugin_id].status = PluginStatus.STOPPED
            except Exception as e:
                logger.error(f"[plugins] Error during shutdown of {plugin_id}: {e}")

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "total_plugins": len(self.plugins),
            "plugins": {pid: info.dict() for pid, info in self.runtime_info.items()}
        }

# Global Singleton
plugin_manager = PluginManager()

class PluginInstaller:
    """Handles runtime installation of new plugins."""
    async def install(self, package_path: str):
        # Future: Implement secure extraction and manifest registration
        pass

class PluginUninstaller:
    """Handles safe removal of plugins."""
    async def uninstall(self, plugin_id: str):
        # Future: Implement cleanup and registry removal
        pass
