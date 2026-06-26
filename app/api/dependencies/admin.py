"""Admin dependency injection helpers.

Wraps the existing auth dependencies to raise AppError instead of
HTTPException, giving consistent JSON error shapes across admin routes.
"""
from app.auth.dependencies import get_current_admin as _get_current_admin
from app.auth.dependencies import get_current_super_admin as _get_current_super_admin
from app.core.errors import AppError
from app.db.models import User
from fastapi import Depends


async def require_admin(current_user: User = Depends(_get_current_admin)) -> User:
    """Require admin role. Raises AppError 403 if not admin."""
    if current_user.role != "admin":
        raise AppError(
            "Admin access required",
            status_code=403,
            code="forbidden",
        )
    return current_user


async def require_super_admin(current_user: User = Depends(require_admin)) -> User:
    """Require super_admin sub-role. Raises AppError 403 if not super_admin."""
    admin_role = getattr(current_user, "admin_role", None)
    if admin_role != "super_admin":
        raise AppError(
            "Super admin access required",
            status_code=403,
            code="forbidden",
        )
    return current_user
