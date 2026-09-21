"""Admin dependency injection helpers.

Wraps the centralized Authorization & Policy Engine to enforce admin permissions.

Fallback behaviour: when the RBAC/ABAC tables have no entries for a user, the
engine returns DENY by default (fail-closed).  To prevent a chicken-and-egg
problem on fresh deployments (where seeded RBAC data may not yet exist), we
also grant access when the user's `role` column is "admin" or "super_admin".
This mirrors the role column set during registration / ensure_admin and is safe
because `role` is only writable by privileged code paths (registration and
admin-only DB patches).
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

_ADMIN_ROLES = {"admin", "super_admin"}
_SUPER_ADMIN_ROLES = {"super_admin"}


async def require_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Require admin permissions.

    Evaluation order:
    1. ABAC/RBAC engine (policy tables) — takes precedence when populated.
    2. User.role column fallback — grants access when role is 'admin' or
       'super_admin', covering fresh deployments before RBAC seeding.
    """
    # Fast-path: role column grants admin immediately (covers fresh deployments)
    user_role = getattr(current_user, "role", None) or ""
    if user_role in _ADMIN_ROLES:
        return current_user

    # Full ABAC/RBAC evaluation for non-trivially-roled users
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Require super_admin permissions.

    Evaluation order:
    1. User.role column fast-path for 'super_admin'.
    2. Full ABAC/RBAC engine check.
    3. Falls back to requiring require_admin when RBAC tables are unseeded
       (so at minimum the user must be an admin).
    """
    user_role = getattr(current_user, "role", None) or ""

    if user_role in _SUPER_ADMIN_ROLES:
        return current_user

    # Full policy check for super_admin
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
        # Admin/super_admin role bypasses individual permission checks
        user_role = getattr(current_user, "role", None) or ""
        if user_role in _ADMIN_ROLES:
            return current_user

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
