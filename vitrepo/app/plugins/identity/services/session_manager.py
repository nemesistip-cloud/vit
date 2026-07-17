import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.plugins.identity.models import IdentitySession, GlobalIdentity
from app.core.event_bus import event_bus

logger = logging.getLogger(__name__)

class SessionManager:
    """Enterprise Session Management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_expire_hours = 24
        self.max_concurrent_sessions = 5

    async def create_session(self,
                             identity: GlobalIdentity,
                             device_id: Optional[str] = None,
                             ip_address: Optional[str] = None,
                             user_agent: Optional[str] = None) -> IdentitySession:
        """Create a new session for an identity."""

        # Enforce concurrent session limits
        active_sessions = await self.get_active_sessions(identity.id)
        if len(active_sessions) >= self.max_concurrent_sessions:
            # Revoke oldest session
            oldest = min(active_sessions, key=lambda s: s.created_at)
            await self.revoke_session(oldest.session_token)

        session_token = secrets.token_urlsafe(64)
        refresh_token = secrets.token_urlsafe(64)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.session_expire_hours)

        new_session = IdentitySession(
            identity_id=identity.id,
            session_token=session_token,
            refresh_token=refresh_token,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
            is_active=True
        )

        self.session.add(new_session)
        await self.session.commit()
        await self.session.refresh(new_session)

        await event_bus.publish("SessionCreated", {
            "gid": identity.gid,
            "session_id": new_session.id,
            "device_id": device_id
        }, sender="session_manager")

        return new_session

    async def validate_session(self, session_token: str) -> Optional[IdentitySession]:
        """Validate and update session activity."""
        result = await self.session.execute(
            select(IdentitySession).where(
                IdentitySession.session_token == session_token,
                IdentitySession.is_active == True,
                IdentitySession.expires_at > datetime.now(timezone.utc)
            )
        )
        session_obj = result.scalar_one_or_none()

        if session_obj:
            session_obj.last_activity = datetime.now(timezone.utc)
            await self.session.commit()
            return session_obj

        return None

    async def revoke_session(self, session_token: str):
        result = await self.session.execute(
            select(IdentitySession).where(IdentitySession.session_token == session_token)
        )
        session_obj = result.scalar_one_or_none()
        if session_obj:
            session_obj.is_active = False
            await self.session.commit()

            # Use identity.gid if available
            await event_bus.publish("SessionRevoked", {
                "session_id": session_obj.id
            }, sender="session_manager")

    async def get_active_sessions(self, identity_id: int) -> List[IdentitySession]:
        result = await self.session.execute(
            select(IdentitySession).where(
                IdentitySession.identity_id == identity_id,
                IdentitySession.is_active == True,
                IdentitySession.expires_at > datetime.now(timezone.utc)
            )
        )
        return list(result.scalars().all())
