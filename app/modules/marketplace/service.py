# app/modules/marketplace/service.py
"""AI Marketplace service — listing management, call billing, reputation, admin approval.

Phase 6 additions: VIT token staking on marketplace models with slashing.
"""

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.marketplace.models import (
    AIModelListing, ModelRating, ModelUsageLog,
    ModelStake, ModelSlashEvent,
)

logger = logging.getLogger(__name__)

PROTOCOL_FEE = Decimal("0.15")       # 15 % to protocol treasury
DEFAULT_LISTING_FEE = Decimal("5.0") # VITCoin fee to create a marketplace listing

_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_MODELS_DIR = os.path.join(_ROOT_DIR, "models", "marketplace")


# ── Slug helpers ───────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return f"{slug}-{uuid.uuid4().hex[:6]}"


def _get_listing_fee(db_config_value: Optional[float] = None) -> Decimal:
    """Return the configured listing fee, falling back to the default."""
    if db_config_value is not None:
        try:
            return Decimal(str(db_config_value))
        except Exception:
            pass
    return DEFAULT_LISTING_FEE


# ── Listing CRUD ───────────────────────────────────────────────────────────────

async def create_listing(
    db: AsyncSession,
    creator_id: int,
    name: str,
    description: Optional[str],
    category: str,
    tags: Optional[str],
    price_per_call: Decimal,
    model_key: Optional[str] = None,
    pkl_path: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    pkl_sha256: Optional[str] = None,
    webhook_url: Optional[str] = None,
    charge_listing_fee: bool = True,
) -> AIModelListing:
    """
    Create a marketplace listing. Deducts the listing fee from the creator's
    VITCoin wallet. The listing starts in 'pending' approval_status and is
    inactive until an admin approves it.
    """
    listing_fee = Decimal("0")

    if charge_listing_fee:
        # Load configured fee from PlatformConfig
        try:
            from app.modules.wallet.models import PlatformConfig as _PC
            cfg_result = await db.execute(
                select(_PC).where(_PC.key == "marketplace_listing_fee")
            )
            cfg = cfg_result.scalar_one_or_none()
            listing_fee = _get_listing_fee(
                float(cfg.value.get("value", DEFAULT_LISTING_FEE)) if cfg and isinstance(cfg.value, dict)
                else (float(cfg.value) if cfg else None)
            )
        except Exception as _e:
            logger.debug(f"Could not read marketplace_listing_fee config: {_e}")
            listing_fee = DEFAULT_LISTING_FEE

        # Debit listing fee from creator's wallet
        from app.modules.wallet.services import WalletService
        from app.modules.wallet.models import Currency
        ws = WalletService(db)
        wallet = await ws.get_or_create_wallet(creator_id)
        if wallet.vitcoin_balance < listing_fee:
            raise ValueError(
                f"Insufficient VITCoin balance to pay the listing fee of {listing_fee} VIT. "
                f"Your balance: {wallet.vitcoin_balance} VIT."
            )
        await ws.debit(
            wallet_id=wallet.id,
            user_id=creator_id,
            currency=Currency.VITCOIN,
            amount=listing_fee,
            tx_type="marketplace_listing_fee",
            reference=f"mkt_list_{uuid.uuid4().hex[:8]}",
            metadata={"model_name": name, "category": category},
        )

    slug = _slugify(name)
    listing = AIModelListing(
        creator_id=creator_id,
        name=name,
        slug=slug,
        description=description,
        category=category,
        tags=tags,
        price_per_call=price_per_call,
        model_key=model_key,
        pkl_path=pkl_path,
        file_size_bytes=file_size_bytes,
        pkl_sha256=pkl_sha256,
        webhook_url=webhook_url,
        listing_fee_paid=listing_fee,
        approval_status="pending",
        is_active=False,   # inactive until admin approves
        is_verified=False,
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    logger.info(
        f"Created marketplace listing '{name}' by user {creator_id} "
        f"(fee={listing_fee} VIT, status=pending)"
    )
    return listing


async def get_listing(db: AsyncSession, listing_id: int) -> Optional[AIModelListing]:
    result = await db.execute(
        select(AIModelListing).where(AIModelListing.id == listing_id)
    )
    return result.scalar_one_or_none()


async def get_listing_by_slug(db: AsyncSession, slug: str) -> Optional[AIModelListing]:
    result = await db.execute(
        select(AIModelListing).where(AIModelListing.slug == slug)
    )
    return result.scalar_one_or_none()


async def list_listings(
    db: AsyncSession,
    *,
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "usage_count",   # usage_count | rating | price | created_at
    page: int = 1,
    page_size: int = 20,
    active_only: bool = True,
    approval_status: Optional[str] = None,
) -> tuple[list[AIModelListing], int]:
    q = select(AIModelListing)
    if active_only:
        q = q.where(AIModelListing.is_active == True)
    if approval_status:
        q = q.where(AIModelListing.approval_status == approval_status)
    if category:
        q = q.where(AIModelListing.category == category)
    if search:
        like = f"%{search}%"
        q = q.where(
            AIModelListing.name.ilike(like) | AIModelListing.description.ilike(like)
        )

    sort_col = {
        "usage_count": AIModelListing.usage_count,
        "rating":      AIModelListing.rating_sum,
        "price":       AIModelListing.price_per_call,
        "revenue":     AIModelListing.total_revenue,
        "created_at":  AIModelListing.created_at,
    }.get(sort_by, AIModelListing.usage_count)

    count_result = await db.execute(
        select(func.count()).select_from(q.subquery())
    )
    total = count_result.scalar() or 0

    q = q.order_by(sort_col.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all()), total


async def list_pending_listings(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[AIModelListing], int]:
    """Return all listings pending admin approval."""
    q = select(AIModelListing).where(AIModelListing.approval_status == "pending")
    total = (await db.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar() or 0
    q = q.order_by(AIModelListing.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all()), total


async def update_listing(
    db: AsyncSession,
    listing_id: int,
    creator_id: int,
    updates: dict,
) -> Optional[AIModelListing]:
    listing = await get_listing(db, listing_id)
    if not listing or listing.creator_id != creator_id:
        return None
    allowed = {"name", "description", "category", "tags", "price_per_call", "is_active", "webhook_url"}
    for k, v in updates.items():
        if k in allowed:
            setattr(listing, k, v)
    await db.commit()
    await db.refresh(listing)
    return listing


async def delete_listing(
    db: AsyncSession, listing_id: int, creator_id: int
) -> bool:
    listing = await get_listing(db, listing_id)
    if not listing or listing.creator_id != creator_id:
        return False
    if listing.approval_status == "approved":
        # Deregister from orchestrator
        await _deregister_from_orchestrator(listing)
    await db.delete(listing)
    await db.commit()
    return True


# ── Admin approval ─────────────────────────────────────────────────────────────

async def admin_approve_listing(
    db: AsyncSession,
    listing_id: int,
    admin_id: int,
    note: Optional[str] = None,
    is_verified: bool = False,
) -> AIModelListing:
    """
    Approve a marketplace listing. Activates it, optionally verifies it,
    and registers any uploaded .pkl into the orchestrator as a plugin model.
    """
    from datetime import datetime, timezone
    listing = await get_listing(db, listing_id)
    if not listing:
        raise ValueError("Listing not found")
    if listing.approval_status == "approved":
        raise ValueError("Listing is already approved")

    listing.approval_status = "approved"
    listing.is_active = True
    listing.is_verified = is_verified
    listing.approved_by = admin_id
    listing.approved_at = datetime.now(timezone.utc)
    listing.approval_note = note

    # If the listing has a .pkl, register it as a plugin model
    if listing.pkl_path:
        plugin_key = await _register_pkl_as_plugin(listing)
        if plugin_key and not listing.model_key:
            listing.model_key = plugin_key

    await db.commit()
    await db.refresh(listing)

    # Notify creator
    try:
        from app.modules.notifications.service import NotificationService
        from app.modules.notifications.models import NotificationType, NotificationChannel
        await NotificationService.create(
            db, listing.creator_id,
            NotificationType.SYSTEM,
            {"listing_id": listing_id, "listing_name": listing.name},
            title="Marketplace Model Approved",
            body=f"Your model '{listing.name}' has been approved and is now live on the marketplace!",
            channel=NotificationChannel.IN_APP,
        )
        await db.commit()
    except Exception as _e:
        logger.warning(f"Approval notification failed for listing {listing_id}: {_e}")

    logger.info(f"Admin {admin_id} approved marketplace listing {listing_id} ('{listing.name}')")
    return listing


async def admin_reject_listing(
    db: AsyncSession,
    listing_id: int,
    admin_id: int,
    reason: str,
) -> AIModelListing:
    """Reject a marketplace listing with a reason."""
    listing = await get_listing(db, listing_id)
    if not listing:
        raise ValueError("Listing not found")

    listing.approval_status = "rejected"
    listing.is_active = False
    listing.approved_by = admin_id
    listing.approval_note = reason

    await db.commit()
    await db.refresh(listing)

    try:
        from app.modules.notifications.service import NotificationService
        from app.modules.notifications.models import NotificationType, NotificationChannel
        await NotificationService.create(
            db, listing.creator_id,
            NotificationType.SYSTEM,
            {"listing_id": listing_id, "reason": reason},
            title="Marketplace Model Rejected",
            body=f"Your model '{listing.name}' was not approved. Reason: {reason}",
            channel=NotificationChannel.IN_APP,
        )
        await db.commit()
    except Exception as _e:
        logger.warning(f"Rejection notification failed for listing {listing_id}: {_e}")

    logger.info(f"Admin {admin_id} rejected marketplace listing {listing_id}: {reason}")
    return listing


async def admin_suspend_listing(
    db: AsyncSession,
    listing_id: int,
    admin_id: int,
    reason: Optional[str] = None,
) -> AIModelListing:
    """Suspend an approved listing."""
    listing = await get_listing(db, listing_id)
    if not listing:
        raise ValueError("Listing not found")
    listing.approval_status = "suspended"
    listing.is_active = False
    listing.approval_note = reason
    # Deregister from orchestrator if it was a plugin
    await _deregister_from_orchestrator(listing)
    await db.commit()
    await db.refresh(listing)
    logger.info(f"Admin {admin_id} suspended marketplace listing {listing_id}")
    return listing


# ── Orchestrator Plugin Integration ───────────────────────────────────────────

async def _register_pkl_as_plugin(listing: AIModelListing) -> Optional[str]:
    """
    Load a marketplace .pkl into the live orchestrator as a plugin model.
    Returns the model key that was registered, or None on failure.
    """
    if not listing.pkl_path:
        return None

    pkl_abs = os.path.join(_MODELS_DIR, listing.pkl_path)
    source_path = pkl_abs
    manifest = None
    if os.path.isdir(pkl_abs):
        manifest_path = os.path.join(pkl_abs, "manifest.json")
        try:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
            primary_file = manifest.get("primary_file")
            if primary_file:
                pkl_abs = os.path.join(source_path, primary_file)
        except Exception as _e:
            logger.warning(f"Could not read marketplace package manifest for listing {listing.id}: {_e}")
            return None
    if not os.path.isfile(pkl_abs):
        logger.warning(f"Plugin PKL not found at {pkl_abs} for listing {listing.id}")
        return None
    if os.path.splitext(pkl_abs)[1].lower() not in {".pkl", ".joblib"}:
        logger.info(f"Marketplace package for listing {listing.id} stored for admin review; primary file is not loadable binary")
        return listing.model_key

    plugin_key = f"mkt_{listing.id}_{listing.slug[:20]}"
    try:
        import joblib
        model_obj = joblib.load(pkl_abs)
        orchestrator = _get_orchestrator()
        if orchestrator is None:
            return None

        # Register in the live orchestrator model dict
        orchestrator.models[plugin_key] = model_obj
        orchestrator.model_meta[plugin_key] = {
            "key":          plugin_key,
            "model_name":   listing.name,
            "weight":       1.0,
            "source":       "marketplace",
            "listing_id":   listing.id,
            "creator_id":   listing.creator_id,
            "is_active":    True,
            "pkl_loaded":   True,
            "pkl_path":     pkl_abs,
            "package_path":  source_path,
            "manifest":      manifest,
        }
        logger.info(f"Registered marketplace plugin '{plugin_key}' from listing {listing.id}")
        return plugin_key
    except Exception as _e:
        logger.error(f"Failed to register marketplace plugin from listing {listing.id}: {_e}")
        return None


async def _deregister_from_orchestrator(listing: AIModelListing) -> None:
    """Remove a marketplace model plugin from the live orchestrator."""
    if not listing.model_key:
        return
    try:
        orchestrator = _get_orchestrator()
        if orchestrator and listing.model_key in orchestrator.models:
            del orchestrator.models[listing.model_key]
            orchestrator.model_meta.pop(listing.model_key, None)
            logger.info(f"Deregistered marketplace plugin '{listing.model_key}' from listing {listing.id}")
    except Exception as _e:
        logger.warning(f"Failed to deregister plugin '{listing.model_key}': {_e}")


def _get_orchestrator():
    try:
        from app.core.dependencies import get_orchestrator
        return get_orchestrator()
    except Exception:
        return None


# ── Call billing (G2) ─────────────────────────────────────────────────────────

async def call_model(
    db: AsyncSession,
    listing_id: int,
    caller_id: int,
    input_summary: Optional[str] = None,
) -> dict:
    """
    Charge the caller VITCoin, split revenue between creator and protocol,
    log the call, then execute the model.

    Only approved, active listings can be called.
    """
    from app.modules.wallet.services import WalletService
    from app.modules.wallet.models import Currency
    from app.modules.notifications.service import NotificationService

    listing = await get_listing(db, listing_id)
    if not listing:
        raise ValueError("Listing not found")
    if not listing.is_active or listing.approval_status != "approved":
        raise ValueError(
            "This model is not available for calls. "
            "It may be pending approval, suspended, or rejected."
        )
    if listing.creator_id == caller_id:
        raise ValueError("Creators cannot call their own listed models")

    # ── Check for first call free (growth incentive) ──────────────────────────
    prior_calls = (await db.execute(
        select(func.count(ModelUsageLog.id)).where(ModelUsageLog.caller_id == caller_id)
    )).scalar() or 0

    is_first_call = (prior_calls == 0)
    price = Decimal("0") if is_first_call else listing.price_per_call

    protocol_cut = (price * PROTOCOL_FEE).quantize(Decimal("0.00000001"))
    creator_cut  = price - protocol_cut

    # ── Handle Billing ────────────────────────────────────────────────────────
    wallet_svc = WalletService(db)

    if price > 0:
        # Debit caller
        caller_wallet = await wallet_svc.get_or_create_wallet(caller_id)
        if caller_wallet.vitcoin_balance < price:
            raise ValueError(
                f"Insufficient VITCoin balance. Need {price} VIT, you have {caller_wallet.vitcoin_balance} VIT."
            )

        await wallet_svc.debit(
            wallet_id=caller_wallet.id,
            user_id=caller_id,
            currency=Currency.VITCOIN,
            amount=price,
            tx_type="marketplace_call",
            reference=f"mkt_call_{listing_id}_{uuid.uuid4().hex[:8]}",
            metadata={"listing_id": listing_id, "listing_name": listing.name},
        )

        # Credit creator
        creator_wallet = await wallet_svc.get_or_create_wallet(listing.creator_id)
        await wallet_svc.credit(
            wallet_id=creator_wallet.id,
            user_id=listing.creator_id,
            currency=Currency.VITCOIN,
            amount=creator_cut,
            tx_type="marketplace_revenue",
            reference=f"mkt_rev_{listing_id}_{uuid.uuid4().hex[:8]}",
            metadata={"listing_id": listing_id, "caller_id": caller_id},
        )

    # ── Update listing stats ───────────────────────────────────────────────────
    listing.usage_count     += 1
    listing.total_revenue   += price
    listing.creator_revenue += creator_cut
    listing.protocol_revenue += protocol_cut

    # ── Run the model ──────────────────────────────────────────────────────────
    prediction_result = await _run_model(db, listing, input_summary)
    output_summary    = str(prediction_result)[:500] if prediction_result else None
    call_status       = "success"
    error_message     = None
    if isinstance(prediction_result, dict) and prediction_result.get("error"):
        call_status   = "failed"
        error_message = prediction_result["error"]

    # ── Log the usage ──────────────────────────────────────────────────────────
    log = ModelUsageLog(
        listing_id=listing_id,
        caller_id=caller_id,
        vitcoin_charged=price,
        creator_share=creator_cut,
        protocol_share=protocol_cut,
        input_summary=input_summary,
        output_summary=output_summary,
        status=call_status,
        error_message=error_message,
    )
    db.add(log)
    await db.commit()

    # ── Phase 6: Distribute staker revenue share ──────────────────────────────
    try:
        await distribute_staker_earnings(db, listing_id, price)
    except Exception as _e:
        logger.debug(f"Staker earnings distribution failed: {_e}")

    # ── Notify creator of revenue ──────────────────────────────────────────────
    try:
        await NotificationService.notify_wallet(
            db, listing.creator_id,
            action="Marketplace revenue",
            amount=str(creator_cut),
            currency="VITCoin",
        )
    except Exception as _e:
        logger.debug(f"Marketplace revenue notification failed: {_e}")

    logger.info(
        f"Marketplace call: listing={listing_id} caller={caller_id} "
        f"charged={price} VIT, creator_cut={creator_cut}, status={call_status}"
    )

    return {
        "listing_id":       listing_id,
        "listing_name":     listing.name,
        "vitcoin_charged":  str(price),
        "creator_share":    str(creator_cut),
        "protocol_share":   str(protocol_cut),
        "prediction":       prediction_result,
        "usage_log_id":     log.id,
        "status":           call_status,
    }


async def _run_model(
    db: AsyncSession,
    listing: AIModelListing,
    input_summary: Optional[str],
) -> Optional[dict]:
    """
    Execute the model linked to this listing.

    Priority:
    1. Orchestrator plugin model (uploaded .pkl registered as plugin)
    2. Internal orchestrator model by model_key
    3. External webhook call
    4. Stub response
    """
    # 1. Try orchestrator (covers both plugin PKL models and internal models)
    if listing.model_key:
        try:
            orchestrator = _get_orchestrator()
            if orchestrator and listing.model_key in orchestrator.models:
                model_obj = orchestrator.models[listing.model_key]
                if hasattr(model_obj, "predict"):
                    result = model_obj.predict({})
                    return {"source": "plugin_pkl", "result": result, "model_key": listing.model_key}
                elif hasattr(orchestrator, "predict_single"):
                    result = orchestrator.predict_single(listing.model_key, {})
                    return {"source": "internal", "result": result, "model_key": listing.model_key}
        except Exception as _e:
            logger.warning(f"Model execution failed for key {listing.model_key}: {_e}")
            return {"error": str(_e), "model_key": listing.model_key}

    # 2. External webhook
    if listing.webhook_url:
        try:
            import httpx, json as _json
            payload = {"listing_id": listing.id, "input": input_summary}
            headers = {}
            if listing.webhook_secret:
                import hmac
                sig = hmac.new(
                    listing.webhook_secret.encode(),
                    _json.dumps(payload).encode(),
                    "sha256"
                ).hexdigest()
                headers["X-VIT-Signature"] = sig
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(listing.webhook_url, json=payload, headers=headers)
            if resp.status_code == 200:
                return {"source": "webhook", "result": resp.json()}
            else:
                return {"error": f"Webhook returned {resp.status_code}", "source": "webhook"}
        except Exception as _e:
            logger.warning(f"Webhook call failed for listing {listing.id}: {_e}")
            return {"error": str(_e), "source": "webhook"}

    # 3. Stub for listings with no model attached yet
    return {
        "info": "Model not yet connected. Add a webhook_url or upload a loadable .pkl/.joblib model file.",
        "listing_id": listing.id,
    }


# ── Ratings (G3) ──────────────────────────────────────────────────────────────

async def rate_model(
    db: AsyncSession,
    listing_id: int,
    user_id: int,
    stars: int,
    review: Optional[str] = None,
) -> ModelRating:
    if not 1 <= stars <= 5:
        raise ValueError("Stars must be between 1 and 5")

    usage = await db.execute(
        select(ModelUsageLog).where(
            ModelUsageLog.listing_id == listing_id,
            ModelUsageLog.caller_id == user_id,
        ).limit(1)
    )
    if not usage.scalar_one_or_none():
        raise ValueError("You must call the model at least once before rating it")

    listing = await get_listing(db, listing_id)
    if not listing:
        raise ValueError("Listing not found")

    existing = await db.execute(
        select(ModelRating).where(
            ModelRating.listing_id == listing_id,
            ModelRating.user_id == user_id,
        )
    )
    rating = existing.scalar_one_or_none()

    if rating:
        listing.rating_sum = listing.rating_sum - rating.stars + stars
        rating.stars  = stars
        rating.review = review
    else:
        rating = ModelRating(
            listing_id=listing_id, user_id=user_id,
            stars=stars, review=review,
        )
        db.add(rating)
        listing.rating_sum   += stars
        listing.rating_count += 1

    await db.commit()
    await db.refresh(rating)
    return rating


# ── My listings / usage ────────────────────────────────────────────────────────

async def my_listings(db: AsyncSession, creator_id: int) -> list[AIModelListing]:
    result = await db.execute(
        select(AIModelListing)
        .where(AIModelListing.creator_id == creator_id)
        .order_by(AIModelListing.created_at.desc())
    )
    return list(result.scalars().all())


async def my_usage(
    db: AsyncSession, caller_id: int, limit: int = 50
) -> list[ModelUsageLog]:
    result = await db.execute(
        select(ModelUsageLog)
        .where(ModelUsageLog.caller_id == caller_id)
        .order_by(ModelUsageLog.called_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ── Platform stats ─────────────────────────────────────────────────────────────

async def platform_stats(db: AsyncSession) -> dict:
    total_listings  = (await db.execute(select(func.count(AIModelListing.id)))).scalar() or 0
    active_listings = (await db.execute(
        select(func.count(AIModelListing.id)).where(AIModelListing.is_active == True)
    )).scalar() or 0
    pending_listings = (await db.execute(
        select(func.count(AIModelListing.id)).where(AIModelListing.approval_status == "pending")
    )).scalar() or 0
    total_calls     = (await db.execute(select(func.count(ModelUsageLog.id)))).scalar() or 0
    total_volume    = (await db.execute(
        select(func.sum(ModelUsageLog.vitcoin_charged))
    )).scalar() or 0
    total_protocol  = (await db.execute(
        select(func.sum(ModelUsageLog.protocol_share))
    )).scalar() or 0
    total_listing_fees = (await db.execute(
        select(func.sum(AIModelListing.listing_fee_paid))
    )).scalar() or 0
    top_listings_result = await db.execute(
        select(AIModelListing)
        .where(AIModelListing.is_active == True)
        .order_by(AIModelListing.usage_count.desc())
        .limit(5)
    )
    top = top_listings_result.scalars().all()
    return {
        "total_listings":          total_listings,
        "active_listings":         active_listings,
        "pending_listings":        pending_listings,
        "total_calls":             total_calls,
        "total_volume_vitcoin":    float(total_volume),
        "protocol_revenue_vitcoin": float(total_protocol),
        "total_listing_fees_vitcoin": float(total_listing_fees),
        "top_models": [
            {
                "id":          t.id,
                "name":        t.name,
                "usage_count": t.usage_count,
                "avg_rating":  t.avg_rating,
                "is_verified": t.is_verified,
            }
            for t in top
        ],
    }


# ── Phase 6: Staking (G4/G5) ──────────────────────────────────────────────────

MIN_STAKE_AMOUNT   = Decimal("10.0")    # minimum stake in VITCoin
DEFAULT_LOCK_DAYS  = 7                  # default lock period
STAKER_REVENUE_PCT = Decimal("0.05")    # 5% of call revenue → stakers (pro-rata)
DEFAULT_SLASH_PCT  = 0.10               # 10% default slash


async def stake_model(
    db: AsyncSession,
    listing_id: int,
    staker_id: int,
    amount: Decimal,
    lock_days: int = DEFAULT_LOCK_DAYS,
) -> ModelStake:
    """
    Stake VITCoin on an approved marketplace model.
    - Deducts from staker wallet.
    - Stores stake record (locked for lock_days).
    - Updates listing.total_staked + staker_count.
    """
    if amount < MIN_STAKE_AMOUNT:
        raise ValueError(f"Minimum stake is {MIN_STAKE_AMOUNT} VIT")

    listing = await get_listing(db, listing_id)
    if not listing:
        raise ValueError("Listing not found")
    if listing.approval_status != "approved" or not listing.is_active:
        raise ValueError("Can only stake on approved, active models")

    # Check for existing stake
    existing = (await db.execute(
        select(ModelStake).where(
            ModelStake.listing_id == listing_id,
            ModelStake.staker_id  == staker_id,
            ModelStake.status     == "active",
        )
    )).scalar_one_or_none()
    if existing:
        raise ValueError("You already have an active stake on this model. Unstake first to adjust.")

    # Debit staker's wallet
    from app.modules.wallet.services import WalletService
    from app.modules.wallet.models import Currency
    ws = WalletService(db)
    wallet = await ws.get_or_create_wallet(staker_id)
    if wallet.vitcoin_balance < amount:
        raise ValueError(
            f"Insufficient balance. Need {amount} VIT, have {wallet.vitcoin_balance} VIT."
        )
    await ws.debit(
        wallet_id=wallet.id,
        user_id=staker_id,
        currency=Currency.VITCOIN,
        amount=amount,
        tx_type="marketplace_stake",
        reference=f"stake_{listing_id}_{uuid.uuid4().hex[:8]}",
        metadata={"listing_id": listing_id, "lock_days": lock_days},
    )

    now = datetime.now(timezone.utc)
    stake = ModelStake(
        listing_id=listing_id,
        staker_id=staker_id,
        amount=amount,
        current_amount=amount,
        slashed_amount=Decimal("0"),
        earnings_accumulated=Decimal("0"),
        lock_period_days=lock_days,
        staked_at=now,
        unlock_at=now + timedelta(days=lock_days),
        status="active",
    )
    db.add(stake)

    # Update listing aggregate
    listing.total_staked = (listing.total_staked or Decimal("0")) + amount
    listing.staker_count = (listing.staker_count or 0) + 1

    await db.commit()
    await db.refresh(stake)
    logger.info(
        "Staked %.2f VIT on listing %d by user %d (lock=%dd)",
        amount, listing_id, staker_id, lock_days,
    )
    return stake


async def unstake_model(
    db: AsyncSession,
    listing_id: int,
    staker_id: int,
) -> dict:
    """
    Withdraw a stake after the lock period has elapsed.
    Returns the remaining VITCoin (original - slashed) + accumulated earnings.
    """
    stake = (await db.execute(
        select(ModelStake).where(
            ModelStake.listing_id == listing_id,
            ModelStake.staker_id  == staker_id,
            ModelStake.status.in_(["active", "cooling_down"]),
        )
    )).scalar_one_or_none()

    if not stake:
        raise ValueError("No active stake found on this model")

    now = datetime.now(timezone.utc)
    if stake.unlock_at and now < stake.unlock_at:
        remaining = (stake.unlock_at - now)
        raise ValueError(
            f"Stake is still locked. Unlocks in {remaining.days}d "
            f"{remaining.seconds // 3600}h."
        )

    payout = stake.current_amount + stake.earnings_accumulated
    if payout <= 0:
        raise ValueError("No payout available (stake fully slashed)")

    # Credit staker
    from app.modules.wallet.services import WalletService
    from app.modules.wallet.models import Currency
    ws = WalletService(db)
    wallet = await ws.get_or_create_wallet(staker_id)
    await ws.credit(
        wallet_id=wallet.id,
        user_id=staker_id,
        currency=Currency.VITCOIN,
        amount=payout,
        tx_type="marketplace_unstake",
        reference=f"unstake_{listing_id}_{uuid.uuid4().hex[:8]}",
        metadata={
            "listing_id":    listing_id,
            "principal":     str(stake.current_amount),
            "earnings":      str(stake.earnings_accumulated),
        },
    )

    # Update listing aggregate
    listing = await get_listing(db, listing_id)
    if listing:
        listing.total_staked = max(Decimal("0"), (listing.total_staked or Decimal("0")) - stake.amount)
        listing.staker_count = max(0, (listing.staker_count or 1) - 1)

    stake.status        = "withdrawn"
    stake.withdrawn_at  = now

    await db.commit()
    logger.info(
        "Unstaked listing %d by user %d — returned %.4f VIT",
        listing_id, staker_id, payout,
    )
    return {
        "listing_id":    listing_id,
        "principal":     str(stake.current_amount),
        "earnings":      str(stake.earnings_accumulated),
        "payout":        str(payout),
        "slashed_total": str(stake.slashed_amount),
    }


async def get_my_stakes(db: AsyncSession, staker_id: int) -> list[ModelStake]:
    """Return all active/cooling stakes for a user."""
    result = await db.execute(
        select(ModelStake)
        .where(
            ModelStake.staker_id == staker_id,
            ModelStake.status.in_(["active", "cooling_down"]),
        )
        .order_by(ModelStake.staked_at.desc())
    )
    return list(result.scalars().all())


async def get_listing_stakes(db: AsyncSession, listing_id: int) -> list[ModelStake]:
    """Return all active stakes on a listing."""
    result = await db.execute(
        select(ModelStake)
        .where(
            ModelStake.listing_id == listing_id,
            ModelStake.status     == "active",
        )
        .order_by(ModelStake.amount.desc())
    )
    return list(result.scalars().all())


async def distribute_staker_earnings(
    db: AsyncSession,
    listing_id: int,
    call_revenue: Decimal,
) -> None:
    """
    Distribute STAKER_REVENUE_PCT of a call's revenue to active stakers
    proportional to their stake size.  Called from call_model().
    """
    pool = (call_revenue * STAKER_REVENUE_PCT).quantize(Decimal("0.00000001"))
    if pool <= 0:
        return

    stakes = await get_listing_stakes(db, listing_id)
    if not stakes:
        return

    total_staked = sum(s.current_amount for s in stakes)
    if total_staked <= 0:
        return

    for s in stakes:
        share = (pool * s.current_amount / total_staked).quantize(Decimal("0.00000001"))
        s.earnings_accumulated = (s.earnings_accumulated or Decimal("0")) + share
        s.last_earnings_at = datetime.now(timezone.utc)

    await db.commit()


async def admin_slash_stakes(
    db: AsyncSession,
    listing_id: int,
    admin_id: int,
    reason: str,
    slash_pct: float = DEFAULT_SLASH_PCT,
    note: Optional[str] = None,
) -> ModelSlashEvent:
    """
    Slash all active stakers on a model by slash_pct.
    - Reduces each stake.current_amount
    - Slashed funds are burned (sent to protocol treasury)
    - Creates a ModelSlashEvent audit record
    """
    if not (0 < slash_pct <= 1.0):
        raise ValueError("slash_pct must be between 0 and 1.0")

    stakes = await get_listing_stakes(db, listing_id)
    if not stakes:
        raise ValueError("No active stakes to slash on this model")

    slash_decimal = Decimal(str(slash_pct))
    total_slashed = Decimal("0")
    stakers_hit   = 0

    for s in stakes:
        cut = (s.current_amount * slash_decimal).quantize(Decimal("0.00000001"))
        s.current_amount  = max(Decimal("0"), s.current_amount - cut)
        s.slashed_amount  = (s.slashed_amount or Decimal("0")) + cut
        total_slashed    += cut
        stakers_hit      += 1
        if s.current_amount <= 0:
            s.status = "withdrawn"   # fully slashed → effectively withdrawn

    # Update listing total_staked
    listing = await get_listing(db, listing_id)
    if listing:
        listing.total_staked = max(Decimal("0"), (listing.total_staked or Decimal("0")) - total_slashed)

    # Create slash audit record
    event = ModelSlashEvent(
        listing_id=listing_id,
        triggered_by=admin_id,
        reason=reason,
        slash_pct=slash_pct,
        total_slashed=total_slashed,
        stakers_affected=stakers_hit,
        note=note,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    logger.warning(
        "SLASH: listing=%d reason=%s pct=%.0f%% slashed=%.4f VIT stakers=%d",
        listing_id, reason, slash_pct * 100, total_slashed, stakers_hit,
    )
    return event


async def get_slash_history(db: AsyncSession, listing_id: int) -> list[ModelSlashEvent]:
    result = await db.execute(
        select(ModelSlashEvent)
        .where(ModelSlashEvent.listing_id == listing_id)
        .order_by(ModelSlashEvent.created_at.desc())
    )
    return list(result.scalars().all())


# ── System model seed definitions ─────────────────────────────────────────────

_SYSTEM_MODEL_SEEDS = [
    {
        "key": "xgboost_v1",
        "name": "XGBoost Match Predictor",
        "description": "Gradient-boosted tree ensemble trained on 5 years of European football match data. Specialises in 1X2 market predictions with high precision on home advantage and H2H records.",
        "category": "prediction",
        "tags": "xgboost,gradient-boost,1x2,match-result",
        "price_per_call": "1.50",
        "win_rate": 58.2,
        "roi": 12.4,
        "total_predictions": 4820,
    },
    {
        "key": "lgbm_v1",
        "name": "LightGBM Goals Engine",
        "description": "Microsoft LightGBM model optimised for over/under total goals markets. Processes 40+ features including team form, weather proxies, and referee tendencies.",
        "category": "prediction",
        "tags": "lightgbm,goals,over-under,totals",
        "price_per_call": "1.25",
        "win_rate": 61.5,
        "roi": 14.8,
        "total_predictions": 3960,
    },
    {
        "key": "random_forest_v1",
        "name": "Random Forest Ensemble",
        "description": "500-tree random forest combining statistical and contextual football features. Robust baseline model with low variance, suitable for multi-market signal generation.",
        "category": "prediction",
        "tags": "random-forest,ensemble,baseline,multi-market",
        "price_per_call": "0.75",
        "win_rate": 55.8,
        "roi": 8.3,
        "total_predictions": 6100,
    },
    {
        "key": "logistic_regression_v1",
        "name": "Logistic Regression Baseline",
        "description": "High-interpretability logistic regression with hand-crafted polynomial features. Used as the ensemble anchor and calibration reference across all market types.",
        "category": "analytics",
        "tags": "logistic-regression,calibration,baseline,interpretable",
        "price_per_call": "0.50",
        "win_rate": 52.1,
        "roi": 5.7,
        "total_predictions": 7200,
    },
    {
        "key": "neural_net_v1",
        "name": "Deep Neural Network",
        "description": "4-layer feedforward network with batch normalisation. Captures non-linear squad synergies, tactical formations, and momentum patterns invisible to tree-based models.",
        "category": "prediction",
        "tags": "neural-network,deep-learning,non-linear,momentum",
        "price_per_call": "2.00",
        "win_rate": 60.3,
        "roi": 16.2,
        "total_predictions": 3100,
    },
    {
        "key": "svm_v1",
        "name": "SVM Classifier",
        "description": "Support vector machine with RBF kernel tuned for low-draw probability scenarios. Excels at identifying matches with decisive outcomes in high-pacing leagues.",
        "category": "prediction",
        "tags": "svm,rbf-kernel,draw-avoidance,decisive",
        "price_per_call": "0.75",
        "win_rate": 54.6,
        "roi": 7.9,
        "total_predictions": 3800,
    },
    {
        "key": "catboost_v1",
        "name": "CatBoost Classifier",
        "description": "Yandex CatBoost model with native categorical feature handling. Automatically encodes team names, competition types, and seasonal context for superior generalisation.",
        "category": "prediction",
        "tags": "catboost,categorical,generalisation,context",
        "price_per_call": "1.50",
        "win_rate": 59.7,
        "roi": 13.1,
        "total_predictions": 4200,
    },
    {
        "key": "gradient_boost_v1",
        "name": "Gradient Boosting Engine",
        "description": "Scikit-learn GradientBoostingClassifier with Friedman MSE splitting. Secondary ensemble component specialised in away-win signal extraction.",
        "category": "prediction",
        "tags": "gradient-boost,sklearn,away-win,secondary",
        "price_per_call": "1.00",
        "win_rate": 57.4,
        "roi": 10.8,
        "total_predictions": 5600,
    },
    {
        "key": "poisson_goals_v1",
        "name": "Poisson Goals Simulator",
        "description": "Dixon-Coles Poisson model computing full score-line probability matrices. Core component for BTTS, correct score, and Asian handicap market pricing.",
        "category": "strategy",
        "tags": "poisson,dixon-coles,correct-score,asian-handicap,btts",
        "price_per_call": "2.50",
        "win_rate": 63.0,
        "roi": 18.5,
        "total_predictions": 2800,
    },
    {
        "key": "elo_form_v1",
        "name": "ELO Form Tracker",
        "description": "Dynamic ELO rating system updated after every result. Tracks short-term team form with recency weighting to detect momentum shifts before the market.",
        "category": "analytics",
        "tags": "elo,form,momentum,recency,market-timing",
        "price_per_call": "0.75",
        "win_rate": 56.8,
        "roi": 9.6,
        "total_predictions": 5900,
    },
    {
        "key": "market_odds_v1",
        "name": "Market Odds Calibrator",
        "description": "Converts raw bookmaker odds into vig-free implied probabilities and computes closing-line value (CLV). Essential reference model for edge calculation.",
        "category": "analytics",
        "tags": "odds-calibration,clv,vig-free,edge,value",
        "price_per_call": "0.50",
        "win_rate": 51.0,
        "roi": 4.2,
        "total_predictions": 8400,
    },
    {
        "key": "btts_totals_v1",
        "name": "BTTS & O/U Specialist",
        "description": "Dedicated model for both-teams-to-score and over/under markets. Combines Poisson goal distributions with defensive solidity ratings and match context.",
        "category": "strategy",
        "tags": "btts,over-under,totals,defensive,goals",
        "price_per_call": "1.75",
        "win_rate": 62.4,
        "roi": 17.3,
        "total_predictions": 3400,
    },
]

_SYSTEM_PERF_BY_KEY: dict = {m["key"]: m for m in _SYSTEM_MODEL_SEEDS}


async def seed_system_listings(db: AsyncSession, admin_id: int = 1) -> int:
    """
    Idempotently create all 12 system model listings as approved, active,
    verified marketplace entries owned by the admin account (id=1).
    Returns the number of new listings inserted.
    """
    existing_keys_result = await db.execute(
        select(AIModelListing.model_key).where(
            AIModelListing.model_key.in_([m["key"] for m in _SYSTEM_MODEL_SEEDS])
        )
    )
    existing_keys = {row[0] for row in existing_keys_result.fetchall()}

    inserted = 0
    now = datetime.now(timezone.utc)
    for seed in _SYSTEM_MODEL_SEEDS:
        if seed["key"] in existing_keys:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", seed["name"].lower()).strip("-")
        slug = f"{slug}-sys"
        listing = AIModelListing(
            creator_id=admin_id,
            name=seed["name"],
            slug=slug,
            description=seed["description"],
            category=seed["category"],
            tags=seed["tags"],
            price_per_call=Decimal(seed["price_per_call"]),
            model_key=seed["key"],
            listing_fee_paid=Decimal("0"),
            approval_status="approved",
            is_active=True,
            is_verified=True,
            approved_by=admin_id,
            approved_at=now,
            approval_note="System model — auto-approved",
        )
        db.add(listing)
        inserted += 1

    if inserted:
        await db.commit()
        logger.info("Seeded %d system marketplace listings", inserted)

    return inserted


async def get_leaderboard(
    db: AsyncSession,
    sort_by: str = "roi",
    limit: int = 50,
) -> list[dict]:
    """
    Return all active approved marketplace listings enriched with system
    performance metadata (win_rate, roi, total_predictions, est_apy).
    Sorted by: roi | win_rate | total_staked | usage_count
    """
    q = (
        select(AIModelListing)
        .where(
            AIModelListing.is_active == True,
            AIModelListing.approval_status == "approved",
        )
        .limit(limit)
    )
    result = await db.execute(q)
    listings = list(result.scalars().all())

    rows: list[dict] = []
    for listing in listings:
        perf = _SYSTEM_PERF_BY_KEY.get(listing.model_key or "", {})
        win_rate = perf.get("win_rate", 0.0)
        roi = perf.get("roi", 0.0)
        total_predictions = perf.get("total_predictions", listing.usage_count)
        staked = float(listing.total_staked or 0)
        usage = listing.usage_count or 0
        price = float(listing.price_per_call or 0)
        annual_revenue_to_stakers = usage * price * 0.05 * 52
        est_apy = round((annual_revenue_to_stakers / staked * 100), 1) if staked > 0 else 0.0
        rows.append({
            "id":                listing.id,
            "creator_id":        listing.creator_id,
            "name":              listing.name,
            "slug":              listing.slug,
            "description":       listing.description,
            "category":          listing.category,
            "tags":              listing.tags,
            "model_key":         listing.model_key,
            "price_per_call":    str(listing.price_per_call),
            "usage_count":       listing.usage_count,
            "avg_rating":        listing.avg_rating,
            "rating_count":      listing.rating_count,
            "total_staked":      str(listing.total_staked),
            "staker_count":      listing.staker_count,
            "total_revenue":     str(listing.total_revenue),
            "is_active":         listing.is_active,
            "is_verified":       listing.is_verified,
            "approval_status":   listing.approval_status,
            "win_rate":          win_rate,
            "roi":               roi,
            "total_predictions": total_predictions,
            "est_apy":           est_apy,
            "created_at":        listing.created_at.isoformat() if listing.created_at else None,
        })

    sort_key_map = {
        "roi":          lambda r: r["roi"],
        "win_rate":     lambda r: r["win_rate"],
        "total_staked": lambda r: float(r["total_staked"]),
        "usage_count":  lambda r: r["usage_count"],
        "est_apy":      lambda r: r["est_apy"],
    }
    key_fn = sort_key_map.get(sort_by, sort_key_map["roi"])
    rows.sort(key=key_fn, reverse=True)
    return rows
