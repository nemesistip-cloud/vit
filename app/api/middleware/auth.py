# app/api/middleware/auth.py
# Supports both legacy API key (x-api-key header) and JWT Bearer tokens
import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
from app.core.errors import error_response

load_dotenv()

API_KEY = os.getenv("API_KEY", "")


def auth_enabled() -> bool:
    api_key = os.getenv("API_KEY", "")
    auth_env = os.getenv("AUTH_ENABLED", "").lower()
    if auth_env == "true":
        return True
    if auth_env == "false":
        return False
    return api_key not in ("", "your_api_key_here")


# JWT auth routes and public endpoints — always open
_ALWAYS_OPEN = (
    "/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico",
    "/auth/register", "/auth/login", "/auth/refresh",
    "/system/status",
)

# Only enforce auth on these API route prefixes
_PROTECTED_PREFIXES = (
    "/analytics", "/history", "/predict", "/result",
    "/training", "/ai", "/odds", "/ai-feed", "/admin",
    "/audit", "/subscription/my-plan", "/subscription/upgrade",
    "/subscription/admin",
)


def _is_valid_jwt(token: str) -> bool:
    """Quick JWT validation without DB lookup (signature check only)."""
    try:
        from app.auth.jwt_utils import decode_token
        payload = decode_token(token)
        return payload is not None and payload.get("type") == "access"
    except Exception:
        return False


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware — accepts either:
    1. JWT Bearer token  (Authorization: Bearer <token>)
    2. Legacy API key   (x-api-key: <key>)
    """

    async def dispatch(self, request: Request, call_next):
        if not auth_enabled():
            return await call_next(request)

        path = request.url.path

        if any(path.startswith(p) for p in _ALWAYS_OPEN):
            return await call_next(request)

        # Pass static frontend assets through
        if not any(path.startswith(pfx) for pfx in _PROTECTED_PREFIXES):
            return await call_next(request)

        # ── Check JWT Bearer first ──────────────────────────────────────
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if _is_valid_jwt(token):
                return await call_next(request)
            return error_response(
                request=request,
                status_code=401,
                code="invalid_token",
                message="Invalid or expired JWT token",
            )

        # ── Fall back to API key ────────────────────────────────────────
        api_key = request.headers.get("x-api-key")
        if not api_key:
            return error_response(
                request=request,
                status_code=401,
                code="authentication_required",
                message="Authentication required. Provide Authorization: Bearer <token> or x-api-key header",
            )

        expected = os.getenv("API_KEY", API_KEY)
        if api_key != expected:
            return error_response(
                request=request,
                status_code=401,
                code="invalid_api_key",
                message="Invalid API key",
            )

        return await call_next(request)


async def verify_api_key(request: Request):
    """Route-level dependency — accepts JWT or API key."""
    if not auth_enabled():
        return True

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if _is_valid_jwt(token):
            return True
        raise HTTPException(status_code=401, detail="Invalid or expired JWT token")

    api_key = request.headers.get("x-api-key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing authentication")

    expected = os.getenv("API_KEY", API_KEY)
    if api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True
