import uuid
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.plugins.identity.models import GlobalIdentity, IdentityType, IdentityStatus, VerificationStatus
from app.core.event_bus import event_bus

logger = logging.getLogger(__name__)

class IdentityManager:
    """Manages Global Identities across the VIT Ecosystem."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_identity(self,
                               type: IdentityType,
                               username: Optional[str] = None,
                               email: Optional[str] = None,
                               display_name: Optional[str] = None,
                               profile: Optional[Dict[str, Any]] = None) -> GlobalIdentity:
        """Create a new authoritative Global Identity."""

        # Generate immutable GID
        gid = f"VIT-ID-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[24:].upper()}"

        identity = GlobalIdentity(
            gid=gid,
            type=type,
            username=username,
            email=email,
            display_name=display_name,
            profile=profile or {},
            status=IdentityStatus.ACTIVE,
            verification_status=VerificationStatus.UNVERIFIED
        )

        self.session.add(identity)
        await self.session.commit()
        await self.session.refresh(identity)

        # Publish Event
        await event_bus.publish("UserRegistered", {
            "gid": identity.gid,
            "type": identity.type,
            "username": identity.username,
            "email": identity.email
        }, sender="identity_manager")

        logger.info(f"[identity] Created new identity: {identity.gid} ({identity.type})")
        return identity

    async def get_by_gid(self, gid: str) -> Optional[GlobalIdentity]:
        result = await self.session.execute(select(GlobalIdentity).where(GlobalIdentity.gid == gid))
        return result.scalar_one_or_none()

    async def update_identity(self, gid: str, updates: Dict[str, Any]) -> Optional[GlobalIdentity]:
        identity = await self.get_by_gid(gid)
        if not identity:
            return None

        for key, value in updates.items():
            if hasattr(identity, key) and key != "gid": # GID is immutable
                setattr(identity, key, value)

        await self.session.commit()
        await self.session.refresh(identity)

        await event_bus.publish("IdentityUpdated", {
            "gid": identity.gid,
            "updates": list(updates.keys())
        }, sender="identity_manager")

        return identity
