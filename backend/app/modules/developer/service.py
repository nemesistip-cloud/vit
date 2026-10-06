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

from app.modules.developer.models import APIKey, APIKeyPlan, APIUsageLog, WebhookEndpoint, WebhookDeliveryLog

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


async def bill_api_call(
    db: AsyncSession,
    api_key_id: int,
    user_id: int,
    plan: str,
) -> tuple[bool, str]:
    """
    G09: Deduct VITCoin for a billable API call.
    Free plan — no charge. Other plans deduct price_per_1k / 1000 VITCoin per call.
    Returns (allowed, reason). Returns (False, 'insufficient_balance') on 402.
    """
    cfg = PLAN_DEFAULTS.get(plan, PLAN_DEFAULTS["free"])
    cost_per_call = cfg["price_per_1k"] / Decimal("1000")
    if cost_per_call <= Decimal("0"):
        return True, "free_plan"

    try:
        from app.modules.wallet.services import WalletService
        service = WalletService(db)
        wallet  = await service.get_or_create_wallet(user_id)

        vitcoin_balance = getattr(wallet, "vitcoin_balance", Decimal("0")) or Decimal("0")
        if Decimal(str(vitcoin_balance)) < cost_per_call:
            logger.warning(
                "API billing: user %s insufficient VITCoin (%.6f < %.6f)",
                user_id, vitcoin_balance, cost_per_call,
            )
            return False, "insufficient_balance"

        # Deduct from wallet
        wallet.vitcoin_balance = Decimal(str(vitcoin_balance)) - cost_per_call
        await db.commit()
        return True, "billed"
    except Exception as exc:
        logger.error("API billing error for user %s: %s — allowing call", user_id, exc)
        return True, "billing_error"


async def list_plans(db: AsyncSession) -> list[APIKeyPlan]:
    result = await db.execute(
        select(APIKeyPlan).where(APIKeyPlan.is_active == True).order_by(APIKeyPlan.id)
    )
    return list(result.scalars().all())


async def regenerate_key(db: AsyncSession, key_id: int, user_id: int) -> tuple[Optional[APIKey], Optional[str]]:
    """Rotates a key: generates a new raw key, updates prefix and hash, resets active status."""
    key = await get_key(db, key_id, user_id)
    if not key:
        return None, None

    raw = _generate_raw_key()
    prefix = raw[:12]
    hashed = _hash_key(raw)

    key.key_prefix = prefix
    key.key_hash = hashed
    key.key_plain = raw
    key.is_active = True
    await db.commit()
    await db.refresh(key)
    logger.info("Developer key rotated: id=%s user=%s prefix=%s", key_id, user_id, prefix)
    return key, raw


async def update_key(
    db: AsyncSession,
    key_id: int,
    user_id: int,
    name: Optional[str] = None,
    plan: Optional[str] = None,
) -> Optional[APIKey]:
    """Updates name or plan on an existing API key."""
    key = await get_key(db, key_id, user_id)
    if not key:
        return None

    if name:
        key.name = name
    if plan and plan in PLAN_DEFAULTS:
        cfg = PLAN_DEFAULTS[plan]
        key.plan = plan
        key.rate_limit_rpm = cfg["rpm"]
        key.rate_limit_rpd = cfg["rpd"]

    await db.commit()
    await db.refresh(key)
    return key


# ── Webhooks CRUD & Dispatch ──────────────────────────────────────────────────

async def list_webhooks(db: AsyncSession, user_id: int) -> list[WebhookEndpoint]:
    result = await db.execute(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.user_id == user_id)
        .order_by(WebhookEndpoint.created_at.desc())
    )
    return list(result.scalars().all())


async def get_webhook(db: AsyncSession, webhook_id: int, user_id: int) -> Optional[WebhookEndpoint]:
    result = await db.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id, WebhookEndpoint.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_webhook(
    db: AsyncSession,
    user_id: int,
    url: str,
    events: list[str],
    description: Optional[str] = None,
) -> WebhookEndpoint:
    secret = "whsec_" + secrets.token_hex(24)
    webhook = WebhookEndpoint(
        user_id=user_id,
        url=url,
        description=description,
        secret=secret,
        events=events or ["prediction.resolved"],
        is_active=True,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    logger.info("Developer webhook created: user=%s url=%s", user_id, url)
    return webhook


async def update_webhook(
    db: AsyncSession,
    webhook_id: int,
    user_id: int,
    url: Optional[str] = None,
    events: Optional[list[str]] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[WebhookEndpoint]:
    webhook = await get_webhook(db, webhook_id, user_id)
    if not webhook:
        return None

    if url is not None:
        webhook.url = url
    if events is not None:
        webhook.events = events
    if description is not None:
        webhook.description = description
    if is_active is not None:
        webhook.is_active = is_active

    await db.commit()
    await db.refresh(webhook)
    return webhook


async def delete_webhook(db: AsyncSession, webhook_id: int, user_id: int) -> bool:
    webhook = await get_webhook(db, webhook_id, user_id)
    if not webhook:
        return False
    await db.delete(webhook)
    await db.commit()
    return True


async def send_test_webhook(
    db: AsyncSession,
    webhook_id: int,
    user_id: int,
    event_type: str = "ping",
    payload: Optional[dict] = None,
) -> tuple[bool, WebhookDeliveryLog]:
    import hmac
    import json
    import time
    import httpx

    webhook = await get_webhook(db, webhook_id, user_id)
    if not webhook:
        raise ValueError("Webhook endpoint not found")

    test_payload = payload or {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "message": "This is a test notification from the VIT Developer Platform.",
            "webhook_id": webhook.id,
            "url": webhook.url,
        },
    }

    body_bytes = json.dumps(test_payload).encode("utf-8")
    signature = hmac.new(webhook.secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-VIT-Signature": f"sha256={signature}",
        "X-VIT-Event": event_type,
        "User-Agent": "VIT-Webhook-Delivery/1.0",
    }

    start_time = time.time()
    status_code = None
    response_body = None
    success = False
    error_msg = None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(webhook.url, content=body_bytes, headers=headers)
            status_code = res.status_code
            response_body = res.text[:1000]
            success = (200 <= status_code < 300)
    except Exception as exc:
        error_msg = str(exc)
        logger.warning("Webhook dispatch failed for id=%s url=%s: %s", webhook.id, webhook.url, exc)

    latency_ms = int((time.time() - start_time) * 1000)

    webhook.last_called_at = datetime.now(timezone.utc)
    if not success:
        webhook.failure_count += 1
    else:
        webhook.failure_count = 0

    log = WebhookDeliveryLog(
        webhook_id=webhook.id,
        user_id=user_id,
        event_type=event_type,
        payload=test_payload,
        status_code=status_code,
        response_body=response_body,
        latency_ms=latency_ms,
        success=success,
        error_message=error_msg,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return success, log


async def list_webhook_logs(
    db: AsyncSession,
    user_id: int,
    webhook_id: Optional[int] = None,
    limit: int = 50,
) -> list[WebhookDeliveryLog]:
    stmt = select(WebhookDeliveryLog).where(WebhookDeliveryLog.user_id == user_id)
    if webhook_id is not None:
        stmt = stmt.where(WebhookDeliveryLog.webhook_id == webhook_id)
    stmt = stmt.order_by(WebhookDeliveryLog.delivered_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
