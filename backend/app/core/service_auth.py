"""
app/core/service_auth.py — Internal Service Authentication

Phase 0: services calling services must identify themselves.

Usage (outgoing call from vitnetwork → vit-ai):
    from app.core.service_auth import make_service_headers
    headers = make_service_headers("vitnetwork")
    async with httpx.AsyncClient() as c:
        r = await c.get(url, headers=headers)

Usage (incoming validation — FastAPI dependency):
    from app.core.service_auth import require_service_token
    @router.get("/internal/foo")
    async def foo(_: None = Depends(require_service_token)):
        ...

The token is a short-lived HMAC-SHA256 signature over:
    "<service_name>:<unix_timestamp_truncated_to_minute>"

Token TTL is 2 minutes (allows 1 minute of clock skew).
Set SERVICE_TOKEN_SECRET in environment to a random 32+ byte string.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from typing import Optional

from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)

_SECRET: Optional[str] = None


def _get_secret() -> str:
    global _SECRET
    if _SECRET is None:
        _SECRET = os.getenv("SERVICE_TOKEN_SECRET", "")
        if not _SECRET:
            logger.warning(
                "[service_auth] SERVICE_TOKEN_SECRET not set — "
                "internal service auth is DISABLED (dev mode only)"
            )
    return _SECRET


def _sign(service_name: str, minute_bucket: int) -> str:
    secret = _get_secret()
    if not secret:
        return "dev-no-secret"
    payload = f"{service_name}:{minute_bucket}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def generate_service_token(service_name: str = "vitnetwork") -> str:
    """Generate a token valid for ~2 minutes."""
    bucket = int(time.time()) // 60
    return f"{service_name}.{bucket}.{_sign(service_name, bucket)}"


def verify_service_token(token: str) -> bool:
    """Validate a service token, accepting the current and previous minute bucket."""
    secret = _get_secret()
    if not secret:
        return True

    try:
        parts = token.split(".")
        if len(parts) != 3:
            return False
        service_name, bucket_str, sig = parts
        bucket = int(bucket_str)
    except (ValueError, AttributeError):
        return False

    now_bucket = int(time.time()) // 60
    for valid_bucket in (now_bucket, now_bucket - 1):
        if bucket == valid_bucket and hmac.compare_digest(sig, _sign(service_name, valid_bucket)):
            return True
    return False


def make_service_headers(service_name: str = "vitnetwork") -> dict[str, str]:
    """Return headers to include in outgoing internal service calls."""
    return {
        "X-VIT-Service-Token": generate_service_token(service_name),
        "X-VIT-Source-Service": service_name,
    }


async def require_service_token(
    x_vit_service_token: Optional[str] = Header(None),
) -> None:
    """
    FastAPI dependency — rejects requests that lack a valid internal service token.
    Apply to routes that should only be called by other VIT services.
    """
    secret = _get_secret()
    if not secret:
        return

    if not x_vit_service_token or not verify_service_token(x_vit_service_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing service token",
        )
