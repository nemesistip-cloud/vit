import os
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
from app.core.plugins.models import PluginManifest

logger = logging.getLogger(__name__)

class PluginDiscovery:
    """Discovers plugins by scanning directories for manifest files."""

    def __init__(self, search_paths: List[str]):
        self.search_paths = [Path(p) for p in search_paths]

    def discover(self) -> Dict[str, PluginManifest]:
        """Scan all search paths and return discovered manifests."""
        discovered: Dict[str, PluginManifest] = {}

        for path in self.search_paths:
            if not path.exists():
                logger.warning(f"[discovery] Search path does not exist: {path}")
                continue

            logger.info(f"[discovery] Scanning: {path}")

            # Look for subdirectories containing manifest.json
            for plugin_dir in path.iterdir():
                if not plugin_dir.is_dir():
                    continue

                manifest_file = plugin_dir / "manifest.json"
                if manifest_file.exists():
                    try:
                        with open(manifest_file, 'r') as f:
                            data = json.load(f)
                            manifest = PluginManifest(**data)
                            discovered[manifest.plugin_id] = manifest
                            logger.info(f"[discovery] Discovered plugin: {manifest.plugin_id} at {plugin_dir}")
                    except Exception as e:
                        logger.error(f"[discovery] Failed to load manifest at {manifest_file}: {e}")

        return discovered
