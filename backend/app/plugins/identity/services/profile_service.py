import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.plugins.identity.services.identity_manager import IdentityManager

logger = logging.getLogger(__name__)

class ProfileService:
    """Manages identity profiles and extended metadata."""

    def __init__(self, session: AsyncSession, identity_manager: IdentityManager):
        self.session = session
        self.identity_manager = identity_manager

    async def get_profile(self, gid: str) -> Optional[Dict[str, Any]]:
        identity = await self.identity_manager.get_by_gid(gid)
        return identity.profile if identity else None

    async def update_profile(self, gid: str, profile_updates: Dict[str, Any]) -> bool:
        identity = await self.identity_manager.get_by_gid(gid)
        if not identity:
            return False

        current_profile = identity.profile.copy()
        current_profile.update(profile_updates)

        await self.identity_manager.update_identity(gid, {"profile": current_profile})
        return True
