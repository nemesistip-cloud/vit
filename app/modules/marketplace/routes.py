# app/modules/marketplace/routes.py
"""AI Marketplace REST API — Module G."""

import json
import hashlib
import logging
import os
import re
import shutil
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_admin
from app.db.database import get_db
from app.db.models import User
from app.modules.marketplace import service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])

_ROOT_DIR    = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_MODELS_DIR  = os.path.join(_ROOT_DIR, "models", "marketplace")
_MAX_PKL_MB  = 100   # maximum .pkl file size in MB
_MAX_UPLOAD_MB = 100
_LISTING_FEE_VIT = Decimal("5.0")  # default listing fee
_ALLOWED_MODEL_EXTENSIONS = {
    ".pkl", ".joblib", ".py", ".json", ".yaml", ".yml", ".txt", ".md", ".csv",
    ".npz", ".npy", ".onnx", ".pt", ".pth", ".h5", ".bin", ".pyd",
}
_SYSTEM_MODEL_KEYS = [
    "xgboost_v1", "lgbm_v1", "random_forest_v1", "logistic_regression_v1",
    "neural_net_v1", "svm_v1", "catboost_v1", "gradient_boost_v1",
    "poisson_goals_v1", "elo_form_v1", "market_odds_v1", "btts_totals_v1",
]


# ── Schemas ─────────────────────────────────────────────────────────────────────

class ListingCreate(BaseModel):
    name:           str              = Field(..., min_length=3, max_length=128)
    description:    Optional[str]   = None
    category:       str              = Field(default="prediction")
    tags:           Optional[str]   = None
    price_per_call: Decimal          = Field(default=Decimal("1.0"), ge=0)
    model_key:      Optional[str]   = None
    webhook_url:    Optional[str]   = None


class ListingUpdate(BaseModel):
    name:           Optional[str]    = None
    description:    Optional[str]   = None
    category:       Optional[str]   = None
    tags:           Optional[str]   = None
    price_per_call: Optional[Decimal] = None
    is_active:      Optional[bool]  = None
    webhook_url:    Optional[str]   = None


class RateModel(BaseModel):
    stars:  int             = Field(..., ge=1, le=5)
    review: Optional[str]  = None


class CallModel(BaseModel):
    input_summary: Optional[str] = Field(None, max_length=500)


class AdminActionBody(BaseModel):
    note:       Optional[str] = None
    is_verified: bool          = False


class AdminRejectBody(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)


def _fmt_listing(l) -> dict:
    return {
        "id":              l.id,
        "creator_id":      l.creator_id,
        "name":            l.name,
        "slug":            l.slug,
        "description":     l.description,
        "category":        l.category,
        "tags":            l.tags,
        "price_per_call":  str(l.price_per_call),
        "listing_fee_paid": str(l.listing_fee_paid),
        "model_key":       l.model_key,
        "pkl_path":        l.pkl_path,
        "file_size_bytes": l.file_size_bytes,
        "webhook_url":     l.webhook_url,
        "usage_count":     l.usage_count,
        "avg_rating":      l.avg_rating,
        "rating_count":    l.rating_count,
        "total_revenue":   str(l.total_revenue),
        "creator_revenue": str(l.creator_revenue),
        "approval_status": l.approval_status,
        "approval_note":   l.approval_note,
        "is_active":       l.is_active,
        "is_verified":     l.is_verified,
        "created_at":      l.created_at.isoformat() if l.created_at else None,
        "approved_at":     l.approved_at.isoformat() if l.approved_at else None,
    }


# ── Config helpers ───────────────────────────────────────────────────────────────

async def _get_listing_fee(db: AsyncSession) -> Decimal:
    """Return the current listing fee from PlatformConfig or the default."""
    try:
        from app.modules.wallet.models import PlatformConfig
        from sqlalchemy import select
        cfg = (await db.execute(
            select(PlatformConfig).where(PlatformConfig.key == "marketplace_listing_fee")
        )).scalar_one_or_none()
        if cfg:
            val = cfg.value
            if isinstance(val, dict):
                return Decimal(str(val.get("value", _LISTING_FEE_VIT)))
            return Decimal(str(val))
    except Exception:
        pass
    return _LISTING_FEE_VIT


# ── Model key list ────────────────────────────────────────────────────────────

_FALLBACK_MODEL_KEYS = _SYSTEM_MODEL_KEYS

@router.get("/model-keys", summary="List registered ML model keys")
async def list_model_keys(db: AsyncSession = Depends(get_db)):
    try:
        from sqlalchemy import text as sa_text
        result = await db.execute(
            sa_text("SELECT DISTINCT model_key FROM model_training_runs WHERE model_key IS NOT NULL ORDER BY model_key")
        )
        keys = [row[0] for row in result.fetchall() if row[0]]
    except Exception:
        keys = []
    return {"keys": _SYSTEM_MODEL_KEYS, "registered_keys": keys}


def _can_upload_marketplace_model(user: User) -> bool:
    if user.role in {"admin", "validator", "developer"}:
        return True
    if user.admin_role in {"super_admin", "admin"}:
        return True
    if user.subscription_tier in {"analyst", "pro", "elite"}:
        return True
    return False


def _safe_upload_name(filename: str) -> str:
    normalized = filename.replace("\\", "/").strip("/")
    if not normalized or normalized.startswith("../") or "/../" in normalized:
        raise HTTPException(400, "Invalid file path in upload.")
    if os.path.isabs(normalized):
        raise HTTPException(400, "Absolute file paths are not allowed.")
    parts = []
    for part in normalized.split("/"):
        clean = re.sub(r"[^A-Za-z0-9._-]", "_", part).strip("._")
        if not clean:
            raise HTTPException(400, "Invalid file name in upload.")
        parts.append(clean)
    return "/".join(parts)


def _validate_python_source(filename: str, content: bytes) -> None:
    try:
        source = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, f"{filename} must be valid UTF-8 Python source.")
    if not any(token in source for token in ["def predict", "def train", "class Model", "class VITModel"]):
        raise HTTPException(
            400,
            f"{filename} must expose def predict, def train, class Model, or class VITModel for review.",
        )


@router.get("/listing-fee", summary="Current VITCoin fee to list a model")
async def get_listing_fee(db: AsyncSession = Depends(get_db)):
    fee = await _get_listing_fee(db)
    return {
        "listing_fee_vitcoin": str(fee),
        "currency":            "VITCoin",
        "description":         "One-time fee charged when you create a marketplace listing.",
    }


# ── Browse & Detail ────────────────────────────────────────────────────────────

@router.get("/models", summary="Browse approved marketplace listings")
async def browse_listings(
    category:  Optional[str] = None,
    search:    Optional[str] = None,
    sort_by:   str = Query(default="usage_count", enum=["usage_count", "rating", "price", "revenue", "created_at"]),
    page:      int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db:        AsyncSession = Depends(get_db),
    _:         User = Depends(get_current_user),
):
    listings, total = await svc.list_listings(
        db, category=category, search=search,
        sort_by=sort_by, page=page, page_size=page_size,
        active_only=True,
    )
    return {
        "items":      [_fmt_listing(l) for l in listings],
        "total":      total,
        "page":       page,
        "page_size":  page_size,
        "pages":      (total + page_size - 1) // page_size if page_size else 1,
    }


@router.get("/models/{listing_id}", summary="Get listing details")
async def get_listing(
    listing_id: int,
    db:         AsyncSession = Depends(get_db),
    _:          User = Depends(get_current_user),
):
    listing = await svc.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _fmt_listing(listing)


# ── Create Listing (with listing fee) ─────────────────────────────────────────

@router.post("/models", summary="List a new AI model (charges listing fee in VITCoin)", status_code=201)
async def create_listing(
    body:           ListingCreate,
    db:             AsyncSession = Depends(get_db),
    current_user:   User = Depends(get_current_user),
):
    """
    Submit a new model to the marketplace. A listing fee is deducted from
    your VITCoin wallet. The model is inactive until an admin approves it.
    """
    if not _can_upload_marketplace_model(current_user):
        raise HTTPException(
            403,
            "Model listings are available to developer, analyst, pro, elite, validator, and admin accounts.",
        )
    try:
        listing = await svc.create_listing(
            db,
            creator_id=current_user.id,
            name=body.name,
            description=body.description,
            category=body.category,
            tags=body.tags,
            price_per_call=body.price_per_call,
            model_key=body.model_key,
            webhook_url=body.webhook_url,
            charge_listing_fee=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _fmt_listing(listing)


# ── Model File Upload ──────────────────────────────────────────────────────────

@router.post(
    "/models/upload",
    summary="Upload a model package and create a marketplace listing",
    status_code=201,
)
async def upload_model_file(
    name:           str     = Form(..., min_length=3, max_length=128),
    description:    Optional[str] = Form(None),
    category:       str     = Form(default="prediction"),
    tags:           Optional[str] = Form(None),
    price_per_call: float   = Form(default=1.0, ge=0),
    webhook_url:    Optional[str] = Form(None),
    model_key:      str = Form(default="xgboost_v1"),
    primary_file:   Optional[str] = Form(None),
    model_files:    list[UploadFile] = File(default=[], description="Model package files"),
    model_file:     Optional[UploadFile] = File(default=None, description="Legacy single model file"),
    db:             AsyncSession = Depends(get_db),
    current_user:   User = Depends(get_current_user),
):
    """
    Upload a model package and register it as a marketplace listing.

    **Rules:**
    - Supported files include .pkl, .joblib, .py, JSON/YAML configs, numpy artifacts, ONNX, PyTorch, and docs
    - Maximum package size: 100 MB
    - A listing fee in VITCoin is deducted from your wallet
    - The listing is inactive until an admin reviews and approves it
    - Loadable .pkl/.joblib artifacts may be registered in the prediction engine after approval
    """
    if not _can_upload_marketplace_model(current_user):
        raise HTTPException(
            403,
            "Model uploads are available to developer, analyst, pro, elite, validator, and admin accounts.",
        )
    webhook_url = webhook_url or None
    if model_key not in _SYSTEM_MODEL_KEYS:
        raise HTTPException(400, "Select one of the 12 supported system model slots.")

    incoming = [*model_files]
    if model_file is not None:
        incoming.append(model_file)
    incoming = [f for f in incoming if f and f.filename]
    if not incoming:
        raise HTTPException(400, "Attach at least one model package file.")

    upload_id = f"user_{current_user.id}_{uuid.uuid4().hex[:8]}"
    package_dir = os.path.join(_MODELS_DIR, upload_id)
    os.makedirs(_MODELS_DIR, exist_ok=True)
    os.makedirs(package_dir, exist_ok=False)

    total_size = 0
    has_runtime = False
    has_source = False
    package_sha = hashlib.sha256()
    files_meta = []

    try:
        for upload in incoming:
            safe_name = _safe_upload_name(upload.filename or "")
            ext = os.path.splitext(safe_name)[1].lower()
            if ext not in _ALLOWED_MODEL_EXTENSIONS:
                raise HTTPException(400, f"{safe_name} uses unsupported file type {ext or '(none)'}.")
            content = await upload.read()
            size_bytes = len(content)
            if size_bytes == 0:
                raise HTTPException(400, f"{safe_name} is empty.")
            total_size += size_bytes
            if total_size > _MAX_UPLOAD_MB * 1024 * 1024:
                raise HTTPException(400, f"Package too large. Maximum size is {_MAX_UPLOAD_MB} MB.")
            if ext in {".pkl", ".joblib"}:
                try:
                    import io as _io
                    import joblib
                    candidate = joblib.load(_io.BytesIO(content))
                    if not (hasattr(candidate, "predict") or hasattr(candidate, "train") or isinstance(candidate, dict)):
                        raise HTTPException(
                            400,
                            f"{safe_name} must contain an object with predict/train or a metadata dictionary.",
                        )
                except HTTPException:
                    raise
                except Exception as _e:
                    raise HTTPException(400, f"Could not load {safe_name}: {_e}")
                has_runtime = True
            if ext == ".py":
                _validate_python_source(safe_name, content)
                has_source = True
            sha256 = hashlib.sha256(content).hexdigest()
            package_sha.update(safe_name.encode("utf-8"))
            package_sha.update(content)
            disk_path = os.path.join(package_dir, safe_name)
            os.makedirs(os.path.dirname(disk_path), exist_ok=True)
            with open(disk_path, "wb") as fh:
                fh.write(content)
            files_meta.append({
                "filename": safe_name,
                "size_bytes": size_bytes,
                "sha256": sha256,
                "primary": False,
            })

        selected_primary = primary_file or next(
            (f["filename"] for f in files_meta if os.path.splitext(f["filename"])[1].lower() in {".pkl", ".joblib"}),
            files_meta[0]["filename"],
        )
        selected_primary = _safe_upload_name(selected_primary)
        if selected_primary not in {f["filename"] for f in files_meta}:
            raise HTTPException(400, "Primary file must be one of the uploaded files.")
        for item in files_meta:
            item["primary"] = item["filename"] == selected_primary

        manifest = {
            "package_id": upload_id,
            "system_model_slot": model_key,
            "primary_file": selected_primary,
            "supported_extensions": sorted(_ALLOWED_MODEL_EXTENSIONS),
            "files": files_meta,
            "execution_status": "binary_loadable" if has_runtime else "source_review_required",
        }
        with open(os.path.join(package_dir, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
    except Exception:
        shutil.rmtree(package_dir, ignore_errors=True)
        raise

    package_hash = package_sha.hexdigest()
    logger.info(f"Saved marketplace model package for user {current_user.id}: {upload_id} ({total_size} bytes)")

    try:
        listing = await svc.create_listing(
            db,
            creator_id=current_user.id,
            name=name,
            description=description,
            category=category,
            tags=tags,
            price_per_call=Decimal(str(price_per_call)),
            model_key=model_key,
            pkl_path=upload_id,
            file_size_bytes=total_size,
            pkl_sha256=package_hash,
            webhook_url=webhook_url,
            charge_listing_fee=True,
        )
    except ValueError as e:
        shutil.rmtree(package_dir, ignore_errors=True)
        raise HTTPException(400, str(e))

    return {
        **_fmt_listing(listing),
        "message": (
            "Model uploaded and listing created successfully. "
            "An admin will review your submission. You will be notified when it's approved."
        ),
        "upload": {
            "package_id": upload_id,
            "primary_file": selected_primary,
            "size_bytes": total_size,
            "sha256": package_hash,
            "system_model_slot": model_key,
            "files": files_meta,
            "has_python_source": has_source,
        },
    }


# ── Update / Delete ────────────────────────────────────────────────────────────

@router.patch("/models/{listing_id}", summary="Update your listing")
async def update_listing(
    listing_id:   int,
    body:         ListingUpdate,
    db:           AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    listing = await svc.update_listing(db, listing_id, current_user.id, updates)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found or not yours")
    return _fmt_listing(listing)


@router.delete("/models/{listing_id}", summary="Remove your listing")
async def delete_listing(
    listing_id:   int,
    db:           AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = await svc.delete_listing(db, listing_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Listing not found or not yours")
    return {"deleted": True}


# ── Call & Rate ────────────────────────────────────────────────────────────────

@router.post("/models/{listing_id}/call", summary="Call a listed model (pays VITCoin)")
async def call_model(
    listing_id:   int,
    body:         CallModel,
    db:           AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await svc.call_model(
            db,
            listing_id=listing_id,
            caller_id=current_user.id,
            input_summary=body.input_summary,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/models/{listing_id}/rate", summary="Rate a model you've used")
async def rate_model(
    listing_id:   int,
    body:         RateModel,
    db:           AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        rating = await svc.rate_model(
            db,
            listing_id=listing_id,
            user_id=current_user.id,
            stars=body.stars,
            review=body.review,
        )
        return {
            "id":         rating.id,
            "listing_id": rating.listing_id,
            "stars":      rating.stars,
            "review":     rating.review,
            "created_at": rating.created_at.isoformat() if rating.created_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── My Listings & Usage ────────────────────────────────────────────────────────

@router.get("/my-listings", summary="My listed models (all statuses)")
async def my_listings(
    db:           AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listings = await svc.my_listings(db, current_user.id)
    return [_fmt_listing(l) for l in listings]


@router.get("/my-usage", summary="My model call history")
async def my_usage(
    limit: int = Query(default=50, ge=1, le=200),
    db:    AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = await svc.my_usage(db, current_user.id, limit=limit)
    return [
        {
            "id":              log.id,
            "listing_id":      log.listing_id,
            "vitcoin_charged": str(log.vitcoin_charged),
            "creator_share":   str(log.creator_share),
            "protocol_share":  str(log.protocol_share),
            "input_summary":   log.input_summary,
            "output_summary":  log.output_summary,
            "status":          log.status,
            "error_message":   log.error_message,
            "called_at":       log.called_at.isoformat() if log.called_at else None,
        }
        for log in logs
    ]


@router.get("/stats", summary="Platform marketplace statistics")
async def marketplace_stats(
    db: AsyncSession = Depends(get_db),
    _:  User = Depends(get_current_user),
):
    return await svc.platform_stats(db)


# ── Admin Endpoints ─────────────────────────────────────────────────────────────

@router.get("/admin/pending", summary="Admin: list all pending listings")
async def admin_list_pending(
    page:      int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db:        AsyncSession = Depends(get_db),
    _:         User = Depends(get_current_admin),
):
    """List all marketplace listings awaiting admin approval."""
    listings, total = await svc.list_pending_listings(db, page=page, page_size=page_size)
    return {
        "items":     [_fmt_listing(l) for l in listings],
        "total":     total,
        "page":      page,
        "page_size": page_size,
    }


@router.patch("/admin/models/{listing_id}/approve", summary="Admin: approve a listing")
async def admin_approve(
    listing_id: int,
    body:       AdminActionBody,
    db:         AsyncSession = Depends(get_db),
    admin:      User = Depends(get_current_admin),
):
    """
    Approve a pending marketplace listing.
    - Sets it to active so users can call it
    - Optionally marks it as 'verified' (quality badge)
    - If the listing has a .pkl, registers it as a plugin model in the prediction engine
    """
    try:
        listing = await svc.admin_approve_listing(
            db,
            listing_id=listing_id,
            admin_id=admin.id,
            note=body.note,
            is_verified=body.is_verified,
        )
        return {
            **_fmt_listing(listing),
            "message": f"Listing '{listing.name}' approved and is now live.",
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.patch("/admin/models/{listing_id}/reject", summary="Admin: reject a listing")
async def admin_reject(
    listing_id: int,
    body:       AdminRejectBody,
    db:         AsyncSession = Depends(get_db),
    admin:      User = Depends(get_current_admin),
):
    """Reject a pending marketplace listing with a reason. Creator is notified."""
    try:
        listing = await svc.admin_reject_listing(
            db, listing_id=listing_id, admin_id=admin.id, reason=body.reason
        )
        return {"rejected": True, "listing_id": listing_id, "reason": body.reason}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.patch("/admin/models/{listing_id}/verify", summary="Admin: grant verified badge")
async def admin_verify(
    listing_id: int,
    db:         AsyncSession = Depends(get_db),
    _:          User = Depends(get_current_admin),
):
    """Grant a 'verified' quality badge to an already-approved listing."""
    listing = await svc.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.approval_status != "approved":
        raise HTTPException(400, "Only approved listings can receive the verified badge.")
    listing.is_verified = True
    await db.commit()
    return {"verified": True, "listing_id": listing_id}


@router.patch("/admin/models/{listing_id}/suspend", summary="Admin: suspend an active listing")
async def admin_suspend(
    listing_id: int,
    body:       AdminRejectBody,
    db:         AsyncSession = Depends(get_db),
    admin:      User = Depends(get_current_admin),
):
    """Suspend an active marketplace listing and deregister any plugin model."""
    try:
        listing = await svc.admin_suspend_listing(
            db, listing_id=listing_id, admin_id=admin.id, reason=body.reason
        )
        return {"suspended": True, "listing_id": listing_id}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/admin/all", summary="Admin: list all listings (all statuses)")
async def admin_list_all(
    approval_status: Optional[str] = None,
    page:            int = Query(default=1, ge=1),
    page_size:       int = Query(default=50, ge=1, le=200),
    db:              AsyncSession = Depends(get_db),
    _:               User = Depends(get_current_admin),
):
    """List all marketplace listings filtered by approval status."""
    listings, total = await svc.list_listings(
        db, active_only=False, approval_status=approval_status,
        page=page, page_size=page_size,
    )
    return {
        "items":     [_fmt_listing(l) for l in listings],
        "total":     total,
        "page":      page,
        "page_size": page_size,
    }
