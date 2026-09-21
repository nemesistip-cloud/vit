import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.plugins.identity.models import GlobalIdentity, IdentityStatus, IdentitySession
from app.plugins.identity.services.identity_manager import IdentityManager
from app.plugins.identity.services.password_service import PasswordService
from app.plugins.identity.services.token_manager import TokenManager
from app.plugins.identity.services.session_manager import SessionManager
from app.plugins.identity.services.mfa_service import MFAService
from app.core.event_bus import event_bus
from app.core.observability.manager import obs_manager

logger = logging.getLogger(__name__)

class AuthenticationManager:
    """Orchestrates authentication flows for the VIT Ecosystem."""

    def __init__(self,
                 session: AsyncSession,
                 identity_manager: IdentityManager,
                 password_service: PasswordService,
                 token_manager: TokenManager,
                 session_manager: SessionManager,
                 mfa_service: MFAService):
        self.session = session
        self.identity_manager = identity_manager
        self.password_service = password_service
        self.token_manager = token_manager
        self.session_manager = session_manager
        self.mfa_service = mfa_service

    async def authenticate_password(self,
                                   identifier: str,
                                   password: str,
                                   context: Dict[str, Any]) -> Tuple[bool, Optional[GlobalIdentity], str]:
        """Authenticate an identity using username/email and password."""

        # Lookup identity
        result = await self.session.execute(
            select(GlobalIdentity).where(
                (GlobalIdentity.email == identifier) | (GlobalIdentity.username == identifier)
            )
        )
        identity = result.scalar_one_or_none()

        if not identity:
            await event_bus.publish("LoginFailed", {"identifier": identifier, "reason": "not_found"}, sender="auth_manager")
            return False, None, "Invalid credentials."

        if identity.status != IdentityStatus.ACTIVE:
            return False, None, f"Account is {identity.status.value}."

        # Verify password (assuming it's stored in security_metadata for now, or we'd have a separate table)
        hashed_password = identity.security_metadata.get("password_hash")
        if not hashed_password or not self.password_service.verify_password(password, hashed_password):
            # Record failed attempt for brute-force protection
            await self._record_failed_attempt(identity)
            await event_bus.publish("LoginFailed", {"gid": identity.gid, "reason": "invalid_password"}, sender="auth_manager")
            return False, None, "Invalid credentials."

        # Success
        await self._reset_failed_attempts(identity)
        await event_bus.publish("LoginSucceeded", {"gid": identity.gid}, sender="auth_manager")

        return True, identity, "Authenticated."

    async def _record_failed_attempt(self, identity: GlobalIdentity):
        metadata = identity.security_metadata.copy()
        count = metadata.get("failed_login_count", 0) + 1
        metadata["failed_login_count"] = count

        if count >= 5:
            identity.status = IdentityStatus.SUSPENDED
            metadata["lockout_until"] = (datetime.now(timezone.utc)).isoformat() # Simple lockout

        identity.security_metadata = metadata
        await self.session.commit()

    async def _reset_failed_attempts(self, identity: GlobalIdentity):
        metadata = identity.security_metadata.copy()
        metadata["failed_login_count"] = 0
        identity.security_metadata = metadata
        await self.session.commit()
