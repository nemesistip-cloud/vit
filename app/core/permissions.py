# app/core/permissions.py — FastAPI permission dependency factories
from fastapi import Depends, HTTPException, status
from app.auth.dependencies import get_current_user, get_current_admin
from app.db.models import User
from app.core.roles import Permission, has_permission, SubscriptionTier, TIER_LIMITS


def require_permission(permission: Permission):
    """Return a FastAPI dependency that enforces the given permission."""
    async def _dep(current_user: User = Depends(get_current_admin)) -> User:
        admin_role = getattr(current_user, "admin_role", None) or "admin"
        if not has_permission(admin_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission.value}",
            )
        return current_user
    return _dep


def require_admin_roles(*allowed_roles: str):
    """Dependency that allows only specific admin roles."""
    async def _dep(current_user: User = Depends(get_current_admin)) -> User:
        admin_role = getattr(current_user, "admin_role", None) or "admin"
        if admin_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(allowed_roles)}",
            )
        return current_user
    return _dep


def require_subscription(min_tier: str):
    """Dependency that enforces a minimum subscription tier."""
    tier_order = {t.value: i for i, t in enumerate(SubscriptionTier)}

    async def _dep(current_user: User = Depends(get_current_user)) -> User:
        user_tier = getattr(current_user, "subscription_tier", "viewer") or "viewer"
        if tier_order.get(user_tier, 0) < tier_order.get(min_tier, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {min_tier} subscription or higher",
            )
        return current_user
    return _dep


def get_user_tier_limits(user: User) -> dict:
    """Return tier limits for a user based on their subscription tier."""
    tier = getattr(user, "subscription_tier", "viewer") or "viewer"
    try:
        return TIER_LIMITS[SubscriptionTier(tier)]
    except (ValueError, KeyError):
        return TIER_LIMITS[SubscriptionTier.VIEWER]
