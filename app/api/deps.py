# app/api/deps.py — compatibility shim
# Re-exports get_current_user from the auth module so existing imports work
from app.auth.dependencies import get_current_user, get_current_admin, get_optional_user

__all__ = ["get_current_user", "get_current_admin", "get_optional_user"]
