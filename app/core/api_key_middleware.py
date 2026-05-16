"""app/core/api_key_middleware.py
Middleware for API Key authentication, rate limiting, and billing.
"""

import time
import logging
from fastapi import Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from app.modules.developer.models import APIKey
from app.modules.developer import service as svc
import hashlib

logger = logging.getLogger(__name__)

# In-memory rate limit store: {(api_key_id, 'rpm'): [timestamps], (api_key_id, 'rpd'): [timestamps]}
_rate_limit_store = {}

def _check_rate_limit(key_id: int, rpm: int, rpd: int) -> bool:
    now = time.time()
    rpm_key = (key_id, "rpm")
    rpd_key = (key_id, "rpd")

    # RPM check
    rpm_list = _rate_limit_store.get(rpm_key, [])
    rpm_list = [t for t in rpm_list if t > now - 60]
    if len(rpm_list) >= rpm:
        return False
    rpm_list.append(now)
    _rate_limit_store[rpm_key] = rpm_list

    # RPD check
    rpd_list = _rate_limit_store.get(rpd_key, [])
    rpd_list = [t for t in rpd_list if t > now - 86400]
    if len(rpd_list) >= rpd:
        return False
    rpd_list.append(now)
    _rate_limit_store[rpd_key] = rpd_list

    return True

async def api_key_auth_middleware(request: Request, call_next):
    api_key_raw = request.headers.get("X-API-Key")
    if not api_key_raw:
        return await call_next(request)

    # Hash and lookup key
    hashed = hashlib.sha256(api_key_raw.encode()).hexdigest()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(APIKey).where(APIKey.key_hash == hashed, APIKey.is_active == True))
        key = result.scalar_one_or_none()

        if not key:
            raise HTTPException(status_code=401, detail="Invalid API Key")

        # Rate limiting
        if not _check_rate_limit(key.id, key.rate_limit_rpm, key.rate_limit_rpd):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Billing
        allowed, reason = await svc.bill_api_call(db, key.id, key.user_id, key.plan)
        if not allowed:
            raise HTTPException(status_code=402, detail="Insufficient VITCoin balance for API plan")

        # Log usage (non-blocking)
        # In a real app, this would be a background task
        await svc.log_usage(
            db, key.id, key.user_id,
            request.url.path, request.method,
            200, # Assuming success for now
            ip_address=request.client.host if request.client else None
        )

    return await call_next(request)
