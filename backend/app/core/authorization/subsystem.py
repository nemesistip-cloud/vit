import logging
from typing import Dict, Any
from app.core.kernel import Subsystem
from app.modules.authz.registry import initialize_registries
from app.modules.authz.models import Role, Permission
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from sqlalchemy import select

logger = logging.getLogger(__name__)

class AuthorizationSubsystem(Subsystem):
    """Subsystem for bootstrapping the VIT Authorization & Policy Engine."""
    name = "authorization"
    dependencies = ["database", "observability"]

    async def _on_initialize(self, config: Dict[str, Any]):
        # Seed the in-memory registries
        initialize_registries()
        logger.info("[kernel] Authorization registries initialized.")

    async def _on_start(self):
        """Ensure built-in roles and permissions are synchronized with the database."""
        from app.modules.authz.registry import role_registry, permission_registry
        from app.modules.authz.models import Role, Permission

        async with AsyncSessionLocal() as session:
            # 1. Sync Permissions
            for perm_def in permission_registry.get_all():
                stmt = select(Permission).where(Permission.slug == perm_def.slug)
                result = await session.execute(stmt)
                if not result.scalar_one_or_none():
                    session.add(Permission(
                        slug=perm_def.slug,
                        description=perm_def.description
                    ))

            # 2. Sync Roles
            for role_def in role_registry.get_all_builtins():
                stmt = select(Role).where(Role.slug == role_def.slug)
                result = await session.execute(stmt)
                if not result.scalar_one_or_none():
                    session.add(Role(
                        slug=role_def.slug,
                        name=role_def.name,
                        description=role_def.description,
                        is_builtin=True
                    ))

            await session.commit()

        logger.info("[kernel] Authorization policies synchronized with database.")

    async def health_check(self) -> bool:
        from app.modules.authz.registry import permission_registry
        return len(permission_registry.get_all()) > 0
