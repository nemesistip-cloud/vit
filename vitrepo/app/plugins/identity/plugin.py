import logging
import json
from pathlib import Path
from typing import Any, Dict, Optional
from app.core.plugins.contract import PluginContract
from app.core.plugins.models import PluginManifest, PluginStatus, Capability
from app.core.plugins.host import extension_host
from app.plugins.identity.services.identity_manager import IdentityManager
from app.plugins.identity.services.authentication_manager import AuthenticationManager
from app.plugins.identity.services.session_manager import SessionManager
from app.plugins.identity.services.token_manager import TokenManager
from app.plugins.identity.services.mfa_service import MFAService
from app.plugins.identity.services.password_service import PasswordService
from app.plugins.identity.services.device_trust_manager import DeviceTrustManager
from app.db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class IdentityPlugin(PluginContract):
    """Authoritative Identity & Authentication Platform Plugin."""

    def __init__(self):
        super().__init__()
        self._manifest = self._load_manifest()
        self.state = PluginStatus.STOPPED

        # Services will be initialized per-request or in activate
        self.identity_manager = None
        self.auth_manager = None
        self.session_manager = None
        self.token_manager = None
        self.mfa_service = None
        self.password_service = None
        self.device_trust_manager = None

    def _load_manifest(self) -> PluginManifest:
        manifest_path = Path(__file__).parent / "manifest.json"
        with open(manifest_path, 'r') as f:
            return PluginManifest(**json.load(f))

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    async def _on_initialize(self, config: Dict[str, Any]):
        logger.info(f"[identity-plugin] Initializing {self.manifest.name}...")

        # Initialize singleton-like services that don't need DB session immediately
        self.password_service = PasswordService()
        self.mfa_service = MFAService()
        self.token_manager = TokenManager(secret_key=config.get("jwt_secret", "DEFAULT_SECRET"))

        # Note: DB-dependent services (IdentityManager, etc.) will be instantiated
        # in the API routes using AsyncSessionLocal

        self.state = PluginStatus.INITIALIZED

    async def activate(self):
        logger.info(f"[identity-plugin] Activating {self.manifest.name}...")

        # Register capabilities with the platform
        for cap_name in self.manifest.capabilities:
            capability = Capability(
                name=cap_name,
                provider_id=self.manifest.plugin_id,
                description=f"Identity capability: {cap_name}"
            )
            # In a real system, the host would handle this during registration
            # but we're doing it explicitly here for the mock.
            from app.core.plugins.host import _registry
            _registry.register(capability, self)

        self.state = PluginStatus.ACTIVE

    async def _on_start(self):
        logger.info(f"[identity-plugin] {self.manifest.name} started.")

    async def _on_stop(self):
        logger.info(f"[identity-plugin] {self.manifest.name} stopped.")
        self.state = PluginStatus.STOPPED

    async def suspend(self):
        self.state = PluginStatus.SUSPENDED

    async def resume(self):
        self.state = PluginStatus.ACTIVE

    async def upgrade(self, new_version: str, config: Dict[str, Any]):
        logger.info(f"[identity-plugin] Upgrading to {new_version}...")

    async def health_check(self) -> bool:
        return self.state == PluginStatus.ACTIVE

    # --- Capability Implementation Bridges ---
    # These methods would be called by other modules via the ExtensionHost

    async def authenticate(self, identifier: str, password: str, context: Dict[str, Any]):
        async with AsyncSessionLocal() as session:
            # Re-instantiate manager for the request session
            # (In a real DI system, this would be cleaner)
            from app.plugins.identity.services.identity_manager import IdentityManager
            im = IdentityManager(session)
            sm = SessionManager(session)
            am = AuthenticationManager(session, im, self.password_service, self.token_manager, sm, self.mfa_service)

            return await am.authenticate_password(identifier, password, context)
