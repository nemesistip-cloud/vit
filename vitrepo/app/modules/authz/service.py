import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, insert
from app.modules.authz.models import Role, Permission, Policy, user_roles, role_permissions, AuthzEffect
from app.core.event_bus import event_bus
from app.modules.authz import events

logger = logging.getLogger(__name__)

class AuthorizationService:
    """Administrative service for managing roles, permissions, and policies."""

    @staticmethod
    async def assign_role_to_user(db: AsyncSession, user_id: int, role_slug: str):
        stmt = select(Role).where(Role.slug == role_slug)
        result = await db.execute(stmt)
        role = result.scalar_one_or_none()

        if not role:
            raise ValueError(f"Role not found: {role_slug}")

        await db.execute(insert(user_roles).values(user_id=user_id, role_id=role.id))
        await db.commit()

        await event_bus.publish(
            events.ROLE_ASSIGNED,
            {"user_id": user_id, "role_slug": role_slug},
            sender="authz_service"
        )
        logger.info(f"[authz] Assigned role {role_slug} to user {user_id}")

    @staticmethod
    async def revoke_role_from_user(db: AsyncSession, user_id: int, role_slug: str):
        stmt = select(Role).where(Role.slug == role_slug)
        result = await db.execute(stmt)
        role = result.scalar_one_or_none()

        if not role:
            raise ValueError(f"Role not found: {role_slug}")

        await db.execute(delete(user_roles).where(
            user_roles.c.user_id == user_id,
            user_roles.c.role_id == role.id
        ))
        await db.commit()

        await event_bus.publish(
            events.ROLE_REVOKED,
            {"user_id": user_id, "role_slug": role_slug},
            sender="authz_service"
        )

    @staticmethod
    async def create_custom_role(db: AsyncSession, slug: str, name: str, description: str = None):
        role = Role(slug=slug, name=name, description=description, is_builtin=False)
        db.add(role)
        await db.commit()
        return role

    @staticmethod
    async def grant_permission_to_role(db: AsyncSession, role_slug: str, permission_slug: str):
        role_stmt = select(Role).where(Role.slug == role_slug)
        role = (await db.execute(role_stmt)).scalar_one_or_none()

        perm_stmt = select(Permission).where(Permission.slug == permission_slug)
        perm = (await db.execute(perm_stmt)).scalar_one_or_none()

        if not role or not perm:
            raise ValueError("Role or Permission not found")

        await db.execute(insert(role_permissions).values(role_id=role.id, permission_id=perm.id))
        await db.commit()

        await event_bus.publish(
            events.PERMISSION_GRANTED,
            {"role_slug": role_slug, "permission_slug": permission_slug},
            sender="authz_service"
        )
