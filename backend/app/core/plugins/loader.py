import importlib.util
import sys
import logging
from pathlib import Path
from typing import Optional, Any, Dict, Type
from app.core.plugins.contract import PluginContract
from app.core.plugins.models import PluginManifest

logger = logging.getLogger(__name__)

class PluginSandbox:
    """Provides isolation for plugin execution."""

    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id

    def wrap_plugin(self, plugin_instance: PluginContract) -> PluginContract:
        """Apply security wrappers to the plugin instance."""
        # Future: Implement proxy objects to restrict access to sensitive platform APIs
        return plugin_instance

class PluginLoader:
    """Handles dynamic loading of plugin modules."""

    def __init__(self, plugin_root: str):
        self.plugin_root = Path(plugin_root)

    def load(self, manifest: PluginManifest) -> Optional[PluginContract]:
        """Dynamically load and instantiate the plugin."""
        plugin_id = manifest.plugin_id
        # Expecting plugin entry point in plugin_dir/plugin.py
        plugin_dir = self.plugin_root / plugin_id.split('.')[-1] # Simple mapping

        # Fallback to search by ID if simple mapping fails
        if not plugin_dir.exists():
            # Try to find a directory that contains a manifest with this ID
            for d in self.plugin_root.iterdir():
                if d.is_dir() and (d / "manifest.json").exists():
                    try:
                        with open(d / "manifest.json", 'r') as f:
                            import json
                            if json.load(f).get("plugin_id") == plugin_id:
                                plugin_dir = d
                                break
                    except: continue

        plugin_file = plugin_dir / "plugin.py"
        if not plugin_file.exists():
            logger.error(f"[loader] Entry point not found for {plugin_id} at {plugin_file}")
            return None

        try:
            module_name = f"app.plugins.dynamic.{plugin_id}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find the Plugin class
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, PluginContract) and
                    attr is not PluginContract):

                    # Instantiate plugin
                    sandbox = PluginSandbox(plugin_id)
                    instance = attr()
                    return sandbox.wrap_plugin(instance)

            logger.error(f"[loader] No class implementing PluginContract found in {plugin_file}")
            return None

        except Exception as e:
            logger.error(f"[loader] Failed to load module for {plugin_id}: {e}")
            return None
