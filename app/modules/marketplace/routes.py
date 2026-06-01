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
from app.services.gcs_storage import gcs_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])

_ROOT_DIR    = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_MODELS_DIR  = os.path.join(_ROOT_DIR, "models", "marketplace")
_MAX_UPLOAD_MB = 100
_ALLOWED_MODEL_EXTENSIONS = {
    ".pkl", ".joblib", ".py", ".json", ".yaml", ".yml", ".txt", ".md", ".csv",
    ".npz", ".npy", ".onnx", ".pt", ".pth", ".h5", ".bin", ".pyd",
}
_SYSTEM_MODEL_KEYS = [
    "xgboost_v1", "lgbm_v1", "random_forest_v1", "logistic_regression_v1",
    "neural_net_v1", "svm_v1", "catboost_v1", "gradient_boost_v1",
    "poisson_goals_v1", "elo_form_v1", "market_odds_v1", "btts_totals_v1",
]

# -- Schemas --

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
        "gcs_uri":         l.gcs_uri,
        "file_size_bytes": l.file_size_bytes,
        "webhook_url":     l.webhook_url,
        "usage_count":     l.usage_count,
        "avg_rating":      l.avg_rating,
        "rating_count":    l.rating_count,
        "total_revenue":   str(l.total_revenue),
        "creator_revenue": str(l.creator_revenue),
        "total_staked":    str(l.total_staked),
        "staker_count":    l.staker_count,
        "approval_status": l.approval_status,
        "approval_note":   l.approval_note,
        "is_active":       l.is_active,
        "is_verified":     l.is_verified,
        "created_at":      l.created_at.isoformat() if l.created_at else None,
        "approved_at":     l.approved_at.isoformat() if l.approved_at else None,
    }

def _can_upload_marketplace_model(user: User) -> bool:
    if user.role in {"admin", "validator", "developer"}:
        return True
    if user.subscription_tier in {"analyst", "pro", "elite"}:
        return True
    return False

def _safe_upload_name(filename: str) -> str:
    normalized = filename.replace("\\", "/").strip("/")
    parts = [re.sub(r"[^A-Za-z0-9._-]", "_", part).strip("._") for part in normalized.split("/") if part]
    return "/".join(parts)

@router.get("/models")
async def browse_listings(
    category:  Optional[str] = None,
    search:    Optional[str] = None,
    sort_by:   str = Query(default="usage_count", enum=["usage_count", "rating", "price", "revenue", "created_at"]),
    page:      int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db:        AsyncSession = Depends(get_db),
    _:         User = Depends(get_current_user),
):
    listings, total = await svc.list_listings(db, category=category, search=search, sort_by=sort_by, page=page, page_size=page_size, active_only=True)
    return {"items": [_fmt_listing(l) for l in listings], "total": total, "page": page, "page_size": page_size}

@router.get("/models/{listing_id}")
async def get_listing(listing_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    listing = await svc.get_listing(db, listing_id)
    if not listing: raise HTTPException(status_code=404, detail="Listing not found")
    return _fmt_listing(listing)

@router.post("/models", status_code=201)
async def create_listing(body: ListingCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not _can_upload_marketplace_model(current_user): raise HTTPException(403, "Insufficient privileges.")
    try:
        listing = await svc.create_listing(db, creator_id=current_user.id, name=body.name, description=body.description, category=body.category, tags=body.tags, price_per_call=body.price_per_call, model_key=body.model_key, webhook_url=body.webhook_url, charge_listing_fee=True)
    except ValueError as e: raise HTTPException(status_code=400, detail=str(e))
    return _fmt_listing(listing)

@router.post("/models/upload", status_code=201)
async def upload_model_file(
    name:           str     = Form(...),
    description:    Optional[str] = Form(None),
    category:       str     = Form(default="prediction"),
    tags:           Optional[str] = Form(None),
    price_per_call: float   = Form(default=1.0),
    webhook_url:    Optional[str] = Form(None),
    model_key:      str = Form(default="xgboost_v1"),
    primary_file:   Optional[str] = Form(None),
    model_files:    list[UploadFile] = File(default=[]),
    model_file:     Optional[UploadFile] = File(default=None),
    db:             AsyncSession = Depends(get_db),
    current_user:   User = Depends(get_current_user),
):
    if not _can_upload_marketplace_model(current_user): raise HTTPException(403, "Insufficient privileges.")
    incoming = [f for f in [*model_files, model_file] if f and f.filename]
    if not incoming: raise HTTPException(400, "Attach at least one model package file.")

    upload_id = f"user_{current_user.id}_{uuid.uuid4().hex[:8]}"
    package_dir = os.path.join(_MODELS_DIR, upload_id)
    os.makedirs(package_dir, exist_ok=True)

    total_size = 0
    files_meta = []
    package_sha = hashlib.sha256()

    for upload in incoming:
        safe_name = _safe_upload_name(upload.filename)
        content = await upload.read()
        total_size += len(content)
        package_sha.update(safe_name.encode())
        package_sha.update(content)
        disk_path = os.path.join(package_dir, safe_name)
        os.makedirs(os.path.dirname(disk_path), exist_ok=True)
        with open(disk_path, "wb") as f: f.write(content)
        files_meta.append({"filename": safe_name, "size_bytes": len(content)})

    selected_primary = primary_file or (files_meta[0]["filename"] if files_meta else "")
    gcs_uri = None
    try:
        bucket = os.getenv("GCS_BUCKET_NAME") or "vit-models"
        for f_meta in files_meta:
            local_f = os.path.join(package_dir, f_meta["filename"])
            await gcs_storage.upload_model(local_f, f"{upload_id}/{f_meta['filename']}")
        gcs_uri = f"gs://{bucket}/{upload_id}/{selected_primary}"
    except Exception as e: logger.error(f"GCS upload failed: {e}")

    listing = await svc.create_listing(db, creator_id=current_user.id, name=name, description=description, category=category, tags=tags, price_per_call=Decimal(str(price_per_call)), model_key=model_key, pkl_path=upload_id, file_size_bytes=total_size, pkl_sha256=package_sha.hexdigest(), gcs_uri=gcs_uri, webhook_url=webhook_url, charge_listing_fee=True)
    return _fmt_listing(listing)

@router.get("/my-listings")
async def my_listings(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    listings = await svc.my_listings(db, current_user.id)
    return [_fmt_listing(l) for l in listings]

@router.get("/leaderboard")
async def leaderboard(sort_by: str = Query(default="roi"), db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return {"items": await svc.get_leaderboard(db, sort_by=sort_by)}
