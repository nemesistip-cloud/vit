import logging
import semver
from typing import List, Dict, Set, Optional
from app.core.plugins.models import PluginManifest

logger = logging.getLogger(__name__)

class DependencyResolver:
    """Resolves and validates the plugin dependency graph."""

    def __init__(self, discovered: Dict[str, PluginManifest]):
        self.discovered = discovered

    def resolve_order(self) -> List[str]:
        """Perform topological sort to determine loading order."""
        visited = set()
        stack = []
        path = set()

        def visit(plugin_id):
            if plugin_id in path:
                raise ValueError(f"Circular plugin dependency detected: {' -> '.join(list(path) + [plugin_id])}")
            if plugin_id in visited:
                return

            if plugin_id not in self.discovered:
                # Optional dependencies might be missing
                return

            path.add(plugin_id)
            manifest = self.discovered[plugin_id]

            # Resolve mandatory dependencies
            for dep_id, version_req in manifest.dependencies.items():
                if dep_id not in self.discovered:
                    raise ValueError(f"Missing mandatory dependency: {plugin_id} requires {dep_id}")

                # Check version compatibility
                dep_manifest = self.discovered[dep_id]
                if not semver.match(dep_manifest.version, version_req):
                    raise ValueError(f"Incompatible dependency version: {plugin_id} requires {dep_id}@{version_req}, but found {dep_manifest.version}")

                visit(dep_id)

            path.remove(plugin_id)
            visited.add(plugin_id)
            stack.append(plugin_id)

        for plugin_id in self.discovered:
            visit(plugin_id)

        return stack

class CompatibilityManager:
    """Ensures platform and inter-plugin compatibility."""

    @staticmethod
    def check_platform(manifest: PluginManifest, platform_version: str) -> bool:
        """Check if plugin is compatible with platform version."""
        try:
            return semver.match(platform_version, f">={manifest.min_runtime_version}")
        except Exception:
            return False

    @staticmethod
    def check_plugin_compatibility(plugin_a: PluginManifest, plugin_b: PluginManifest) -> bool:
        """Future: Check for known conflicts between specific plugins."""
        return True
