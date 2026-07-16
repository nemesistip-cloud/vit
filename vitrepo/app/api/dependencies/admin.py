"""Admin dependency injection helpers.

Wraps the centralized Authorization & Policy Engine to enforce admin permissions.
"""
import logging
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.errors import AppError
from app.db.database import get_db
from app.db.models import User
from app.modules.authz.manager import authz_manager

logger = logging.getLogger(__name__)

async def require_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Require admin permissions.
    """
    is_allowed = await authz_manager.check_permission(
        db=db,
        user_id=current_user.id,
        action="admin.access"
    )

    if not is_allowed:
        logger.warning(f"Unauthorized admin access attempt by user {current_user.id}")
        raise AppError(
            "Admin access required",
            status_code=403,
            code="forbidden",
        )
    return current_user


async def require_super_admin(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Require super_admin permissions.
    """
    is_allowed = await authz_manager.check_permission(
        db=db,
        user_id=current_user.id,
        action="admin.super"
    )

    if not is_allowed:
        logger.warning(f"Unauthorized super-admin access attempt by user {current_user.id}")
        raise AppError(
            "Super admin access required",
            status_code=403,
            code="forbidden",
        )
    return current_user

def require_permission(permission: str, resource: str = "*"):
    """Enforce a specific permission within the admin context."""
    async def _dep(
        current_user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        is_allowed = await authz_manager.check_permission(
            db=db,
            user_id=current_user.id,
            action=permission,
            resource=resource
        )
        if not is_allowed:
            raise AppError(
                f"Missing permission: {permission}",
                status_code=403,
                code="insufficient_permissions"
            )
        return current_user
    return _dep
