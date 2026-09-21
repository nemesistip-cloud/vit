import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.plugins.identity.models import GlobalIdentity, IdentityStatus

logger = logging.getLogger(__name__)

class UserDirectory:
    """Enterprise User Directory for searching and listing identities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_identities(self, status: Optional[IdentityStatus] = None, limit: int = 100) -> List[GlobalIdentity]:
        query = select(GlobalIdentity)
        if status:
            query = query.where(GlobalIdentity.status == status)

        result = await self.session.execute(query.limit(limit))
        return list(result.scalars().all())

    async def search_identities(self, query_str: str) -> List[GlobalIdentity]:
        """Search identities by username, email, or display name."""
        search = f"%{query_str}%"
        query = select(GlobalIdentity).where(
            (GlobalIdentity.username.ilike(search)) |
            (GlobalIdentity.email.ilike(search)) |
            (GlobalIdentity.display_name.ilike(search))
        )

        result = await self.session.execute(query.limit(50))
        return list(result.scalars().all())
