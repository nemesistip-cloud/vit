# app/modules/marketplace/service.py
"""AI Marketplace service — listing management, call billing, reputation, admin approval."""

import hashlib
import json
import logging
import os
import re
import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.marketplace.models import AIModelListing, ModelRating, ModelUsageLog

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

    price        = listing.price_per_call
    protocol_cut = (price * PROTOCOL_FEE).quantize(Decimal("0.00000001"))
    creator_cut  = price - protocol_cut

    # ── Debit caller ──────────────────────────────────────────────────────────
    wallet_svc   = WalletService(db)
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

    # ── Credit creator ─────────────────────────────────────────────────────────
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
