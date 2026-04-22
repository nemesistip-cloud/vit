# app/modules/developer/service.py
"""Developer Platform service — API key management, usage tracking, billing."""

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.developer.models import APIKey, APIKeyPlan, APIUsageLog

logger = logging.getLogger(__name__)

PLAN_DEFAULTS = {
    "free":       {"rpm": 60,   "rpd": 1_000,  "price_per_1k": Decimal("0.00")},
    "starter":    {"rpm": 120,  "rpd": 5_000,  "price_per_1k": Decimal("0.50")},
    "pro":        {"rpm": 300,  "rpd": 50_000, "price_per_1k": Decimal("0.20")},
    "enterprise": {"rpm": 1000, "rpd": 500_000,"price_per_1k": Decimal("0.10")},
}


# ── Key generation ─────────────────────────────────────────────────────────────

def _generate_raw_key() -> str:
    """Returns a 48-char URL-safe API key with 'vit_' prefix."""
    return "vit_" + secrets.token_urlsafe(36)


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Seed plans ────────────────────────────────────────────────────────────────

async def seed_plans(db: AsyncSession) -> None:
    existing = (await db.execute(select(func.count(APIKeyPlan.id)))).scalar() or 0
    if existing > 0:
        return
    for name, cfg in PLAN_DEFAULTS.items():
        plan = APIKeyPlan(
            name=name,
            display_name=name.capitalize(),
            rate_limit_rpm=cfg["rpm"],
            rate_limit_rpd=cfg["rpd"],
            price_vitcoin_per_1k=cfg["price_per_1k"],
            description=f"{cfg['rpd']} req/day @ {cfg['rpm']} req/min",
        )
        db.add(plan)
    await db.commit()
    logger.info("Developer: seeded 4 default API plans")


# ── API Key CRUD ──────────────────────────────────────────────────────────────

async def create_key(
    db: AsyncSession,
    user_id: int,
    name: str,
    plan: str = "free",
    expires_at: Optional[datetime] = None,
) -> tuple[APIKey, str]:
    """Returns (APIKey, raw_key). raw_key shown once, then discarded."""
    if plan not in PLAN_DEFAULTS:
        raise ValueError(f"Unknown plan '{plan}'. Valid: {list(PLAN_DEFAULTS)}")

    cfg = PLAN_DEFAULTS[plan]
    raw = _generate_raw_key()
    prefix = raw[:12]
    hashed = _hash_key(raw)

    key = APIKey(
        user_id=user_id,
        name=name,
        key_prefix=prefix,
        key_hash=hashed,
        key_plain=raw,   # stored temporarily — cleared after first retrieval
        plan=plan,
        rate_limit_rpm=cfg["rpm"],
        rate_limit_rpd=cfg["rpd"],
        is_active=True,
        expires_at=expires_at,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    logger.info(f"Developer key created: user={user_id} plan={plan} prefix={prefix}")
    return key, raw


async def list_keys(db: AsyncSession, user_id: int) -> list[APIKey]:
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == user_id)
        .order_by(APIKey.created_at.desc())
    )
    return list(result.scalars().all())


async def get_key(db: AsyncSession, key_id: int, user_id: int) -> Optional[APIKey]:
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def revoke_key(db: AsyncSession, key_id: int, user_id: int) -> bool:
    key = await get_key(db, key_id, user_id)
    if not key:
        return False
    key.is_active = False
    await db.commit()
    return True


async def delete_key(db: AsyncSession, key_id: int, user_id: int) -> bool:
    key = await get_key(db, key_id, user_id)
    if not key:
        return False
    await db.delete(key)
    await db.commit()
    return True


# ── Usage logging ─────────────────────────────────────────────────────────────

async def log_usage(
    db: AsyncSession,
    api_key_id: int,
    user_id: int,
    endpoint: str,
    method: str,
    status_code: int,
    latency_ms: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> APIUsageLog:
    key = await db.get(APIKey, api_key_id)
    if key:
        key.total_requests += 1
        key.last_used_at = datetime.now(timezone.utc)

    log = APIUsageLog(
        api_key_id=api_key_id,
        user_id=user_id,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        latency_ms=latency_ms,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def my_usage(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
) -> list[APIUsageLog]:
    result = await db.execute(
        select(APIUsageLog)
        .where(APIUsageLog.user_id == user_id)
        .order_by(APIUsageLog.called_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def usage_summary(db: AsyncSession, user_id: int) -> dict:
    total_calls = (await db.execute(
        select(func.count(APIUsageLog.id)).where(APIUsageLog.user_id == user_id)
    )).scalar() or 0

    success_calls = (await db.execute(
        select(func.count(APIUsageLog.id)).where(
            APIUsageLog.user_id == user_id,
            APIUsageLog.status_code < 400,
        )
    )).scalar() or 0

    total_keys = (await db.execute(
        select(func.count(APIKey.id)).where(APIKey.user_id == user_id)
    )).scalar() or 0

    active_keys = (await db.execute(
        select(func.count(APIKey.id)).where(
            APIKey.user_id == user_id, APIKey.is_active == True
        )
    )).scalar() or 0

    return {
        "total_api_calls": total_calls,
        "successful_calls": success_calls,
        "error_calls": total_calls - success_calls,
        "success_rate": round(success_calls / total_calls * 100, 2) if total_calls else 100.0,
        "total_keys": total_keys,
        "active_keys": active_keys,
    }


async def platform_stats(db: AsyncSession) -> dict:
    total_keys  = (await db.execute(select(func.count(APIKey.id)))).scalar() or 0
    active_keys = (await db.execute(
        select(func.count(APIKey.id)).where(APIKey.is_active == True)
    )).scalar() or 0
    total_calls = (await db.execute(select(func.count(APIUsageLog.id)))).scalar() or 0
    total_users = (await db.execute(
        select(func.count(func.distinct(APIKey.user_id)))
    )).scalar() or 0
    return {
        "total_keys":    total_keys,
        "active_keys":   active_keys,
        "total_api_calls": total_calls,
        "total_developers": total_users,
    }


async def list_plans(db: AsyncSession) -> list[APIKeyPlan]:
    result = await db.execute(
        select(APIKeyPlan).where(APIKeyPlan.is_active == True).order_by(APIKeyPlan.id)
    )
    return list(result.scalars().all())
