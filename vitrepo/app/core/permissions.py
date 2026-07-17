# app/core/permissions.py — FastAPI permission dependency factories
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_current_admin
from app.db.database import get_db
from app.db.models import User
from app.modules.authz.manager import authz_manager


def require_permission(permission: str, resource: str = "*"):
    """
    Return a FastAPI dependency that enforces the given permission
    using the centralized Authorization & Policy Engine.
    """
    async def _dep(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        # Evaluate using the Policy Engine
        context = {
            "user": {
                "id": current_user.id,
                "tier": getattr(current_user, "subscription_tier", "basic"),
                "is_active": current_user.is_active
            }
        }

        is_allowed = await authz_manager.check_permission(
            db=db,
            user_id=current_user.id,
            action=permission,
            resource=resource,
            context=context
        )

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Missing permission '{permission}' for resource '{resource}'",
            )

        return current_user
    return _dep


def require_admin_permission(permission: str, resource: str = "*"):
    """Dependency that enforces a permission specifically for admin users."""
    async def _dep(
        current_user: User = Depends(get_current_admin),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        is_allowed = await authz_manager.check_permission(
            db=db,
            user_id=current_user.id,
            action=permission,
            resource=resource
        )

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Admin Access Denied: Missing permission '{permission}'",
            )

        return current_user
    return _dep
