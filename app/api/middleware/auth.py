# app/api/middleware/auth.py
# Supports both legacy API key (x-api-key header) and JWT Bearer tokens
# SEC-04: Blocklist check on every request — revoked tokens are rejected.
# G09:  vit_* developer API keys are DB-authenticated and billed per call.
import hashlib
import logging
import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
from app.core.errors import error_response

logger = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.getenv("API_KEY", "")


async def _auth_developer_api_key(raw_key: str) -> tuple[bool, str, int | None, str]:
    """
    G09: Authenticate a vit_* developer API key against the DB.
    Returns (allowed, reason, user_id, plan).
    Deducts VITCoin for billable plans; returns allowed=False on 402.
    """
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    try:
        from app.db.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.modules.developer.models import APIKey
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(APIKey).where(
                    APIKey.key_hash == key_hash,
                    APIKey.is_active == True,
                )
            )
            key_record = result.scalar_one_or_none()
            if not key_record:
                return False, "invalid_key", None, "free"

            # Check expiry
            if key_record.expires_at:
                from datetime import datetime, timezone
                exp = key_record.expires_at
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > exp:
                    return False, "key_expired", None, "free"

            user_id = key_record.user_id
            plan    = key_record.plan

            # G09: Deduct VITCoin for billable calls
            from app.modules.developer.service import bill_api_call
            allowed, reason = await bill_api_call(db, key_record.id, user_id, plan)
            return allowed, reason, user_id, plan
    except Exception as exc:
        logger.error("Developer API key auth error: %s — allowing request", exc)
        return True, "auth_error", None, "free"


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
    "/training", "/ai", "/odds", "/admin",
    "/audit", "/subscription/my-plan", "/subscription/upgrade",
    "/subscription/admin",
)

# Public sub-paths within otherwise-protected prefixes
_PUBLIC_SUBPATHS = (
    "/ai-feed/health",
    "/ai-feed/sources",
    "/ai-feed/matches",
    "/ai-feed/recent",
)


async def _validate_jwt(token: str) -> bool:
    """Async JWT validation: checks signature + blocklist (SEC-04)."""
    try:
        from app.auth.jwt_utils import decode_token, is_token_revoked
        payload = decode_token(token)
        if payload is None or payload.get("type") != "access":
            return False
        jti = payload.get("jti")
        if jti:
            from app.db.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                if await is_token_revoked(jti, db):
                    return False
        return True
    except Exception as exc:
        logger.warning("JWT validation error: %s", exc, exc_info=True)
        return False


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware — accepts:
    1. JWT Bearer token        (Authorization: Bearer <token>)
    2. Developer API key      (x-api-key: vit_*  — DB-authenticated + G09 billing)
    3. Legacy env-var API key (x-api-key: <API_KEY env var>)
    """

    async def dispatch(self, request: Request, call_next):
        if not auth_enabled():
            return await call_next(request)

        path = request.url.path

        if any(path.startswith(p) for p in _ALWAYS_OPEN):
            return await call_next(request)

        # Explicitly public sub-paths (even if prefix is protected)
        if any(path == p or path.startswith(p) for p in _PUBLIC_SUBPATHS):
            return await call_next(request)

        # Pass static frontend assets through
        if not any(path.startswith(pfx) for pfx in _PROTECTED_PREFIXES):
            return await call_next(request)

        # ── Check JWT Bearer first ──────────────────────────────────────
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if await _validate_jwt(token):
                return await call_next(request)
            return error_response(
                request=request,
                status_code=401,
                code="invalid_token",
                message="Invalid, expired, or revoked JWT token",
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

        # G09: Developer API keys (vit_* prefix) — DB lookup + billing
        if api_key.startswith("vit_"):
            allowed, reason, _uid, _plan = await _auth_developer_api_key(api_key)
            if not allowed:
                if reason == "insufficient_balance":
                    return error_response(
                        request=request,
                        status_code=402,
                        code="insufficient_balance",
                        message="Insufficient VITCoin balance to make API calls on your current plan.",
                    )
                return error_response(
                    request=request,
                    status_code=401,
                    code="invalid_api_key",
                    message=f"Developer API key rejected: {reason}",
                )
            return await call_next(request)

        # Legacy env-var key — SEC-08: timing-safe comparison prevents oracle attacks
        import hmac as _hmac
        expected = os.getenv("API_KEY", API_KEY)
        if not _hmac.compare_digest(api_key.encode(), expected.encode()):
            return error_response(
                request=request,
                status_code=401,
                code="invalid_api_key",
                message="Invalid API key",
            )

        return await call_next(request)


async def verify_api_key(request: Request):
    """Route-level dependency — accepts JWT, developer vit_* key, or legacy env API key."""
    if not auth_enabled():
        return True

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if await _validate_jwt(token):
            return True
        raise HTTPException(status_code=401, detail="Invalid, expired, or revoked JWT token")

    api_key = request.headers.get("x-api-key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing authentication")

    # G09: developer keys
    if api_key.startswith("vit_"):
        allowed, reason, _uid, _plan = await _auth_developer_api_key(api_key)
        if not allowed:
            status = 402 if reason == "insufficient_balance" else 401
            raise HTTPException(status_code=status, detail=f"Developer API key rejected: {reason}")
        return True

    import hmac as _hmac
    expected = os.getenv("API_KEY", API_KEY)
    if not _hmac.compare_digest(api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True
