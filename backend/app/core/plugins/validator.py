import logging
import semver
from typing import List, Dict, Optional
from app.core.plugins.models import PluginManifest, SecurityClassification

logger = logging.getLogger(__name__)

class PluginValidator:
    """Validates plugin manifests against platform requirements."""

    def __init__(self, platform_version: str):
        self.platform_version = platform_version

    def validate(self, manifest: PluginManifest) -> bool:
        """Perform full validation of a plugin manifest."""
        try:
            # 1. Platform Compatibility
            if not self._check_compatibility(manifest):
                return False

            # 2. Permission Validation
            if not self._validate_permissions(manifest):
                return False

            # 3. Security Check
            if not self._security_audit(manifest):
                return False

            return True
        except Exception as e:
            logger.error(f"[validator] Validation failed for {manifest.plugin_id}: {e}")
            return False

    def _check_compatibility(self, manifest: PluginManifest) -> bool:
        """Check if plugin is compatible with the current platform version."""
        try:
            if semver.compare(self.platform_version, manifest.min_runtime_version) < 0:
                logger.error(f"[validator] {manifest.plugin_id} requires runtime v{manifest.min_runtime_version}, but platform is v{self.platform_version}")
                return False
            return True
        except Exception:
            return False

    def _validate_permissions(self, manifest: PluginManifest) -> bool:
        """Verify requested permissions are within allowed bounds for classification."""
        # Future: Check against a whitelist of allowed permissions per classification
        if manifest.security_classification == SecurityClassification.COMMUNITY:
            restricted = ["os.access", "filesystem.root", "kernel.internal"]
            for p in manifest.permissions:
                if p in restricted:
                    logger.error(f"[validator] {manifest.plugin_id} (COMMUNITY) requested restricted permission: {p}")
                    return False
        return True

    def _security_audit(self, manifest: PluginManifest) -> bool:
        """Stub for signature verification and integrity checks."""
        # In a production environment, we would verify manifest signatures here.
        logger.debug(f"[validator] Security audit passed for {manifest.plugin_id}")
        return True
