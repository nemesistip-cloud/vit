from __future__ import annotations
import hashlib
import json
import logging
import os
import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_user, get_current_admin
from app.modules.marketplace.models import AIModelListing
from app.modules.marketplace import service as svc
from app.services.tachyon_client import tachyon_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/marketplace", tags=["AI Marketplace"])

_MODELS_DIR = "models/marketplace"
_ALLOWED_MODEL_EXTENSIONS = {".pkl", ".joblib", ".py", ".json", ".yaml", ".onnx", ".pt"}
_SYSTEM_MODEL_KEYS = {"xgboost_v1", "rf_v1", "lstm_v1", "ensemble_v1"}

def _fmt_listing(l: AIModelListing) -> dict:
    return {
        "id": l.id, "name": l.name, "slug": l.slug, "description": l.description,
        "category": l.category, "price_per_call": str(l.price_per_call),
        "model_key": l.model_key, "gcs_uri": l.gcs_uri, "is_active": l.is_active
    }

def _can_upload_marketplace_model(user: User) -> bool:
    return getattr(user, "role", "user") in {"admin", "analyst", "pro"}

def _safe_upload_name(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in "._-").strip()

@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)):
    listings, _ = await svc.list_listings(db, active_only=True)
    return [_fmt_listing(l) for l in listings]

@router.post("/models/upload", status_code=201)
async def upload_model_file(
    name: str = Form(...), description: Optional[str] = Form(None),
    category: str = Form(default="prediction"), tags: Optional[str] = Form(None),
    price_per_call: float = Form(default=1.0), webhook_url: Optional[str] = Form(None),
    model_key: str = Form(default="xgboost_v1"), primary_file: Optional[str] = Form(None),
    model_files: list[UploadFile] = File(default=[]), model_file: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    if not _can_upload_marketplace_model(current_user):
        raise HTTPException(403, "Only verified analysts can upload models.")

    files_meta = []
    package_sha = hashlib.sha256()

    incoming = [*model_files]
    if model_file: incoming.append(model_file)

    for upload in incoming:
        if not upload.filename: continue
        fname = _safe_upload_name(upload.filename)
        data = await upload.read()
        package_sha.update(data)

        # Sync to Tachyon distributed storage directly from memory
        tachyon_file_id = await tachyon_client.upload_bytes(data, fname)
        files_meta.append({"filename": fname, "primary": fname == primary_file, "tachyon_id": tachyon_file_id})

    primary_fname = primary_file or (files_meta[0]["filename"] if files_meta else "model.pkl")
    primary_meta = next((m for m in files_meta if m.get("primary") or m["filename"] == primary_fname), {})
    tachyon_id = primary_meta.get("tachyon_id") or uuid.uuid4().hex
    tachyon_uri = f"tachyon://{tachyon_id}/{primary_fname}"

    listing = await svc.create_listing(
        db, creator_id=current_user.id, name=name, description=description,
        category=category, tags=tags, price_per_call=Decimal(str(price_per_call)),
        model_key=model_key, pkl_path=tachyon_id, pkl_sha256=package_sha.hexdigest(),
        gcs_uri=tachyon_uri, webhook_url=webhook_url
    )

    return {**_fmt_listing(listing), "message": "Model uploaded and synced to Tachyon."}

@router.get("/my-listings")
async def my_listings(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    listings = await svc.my_listings(db, current_user.id)
    return [_fmt_listing(l) for l in listings]


@router.get("/stats")
async def marketplace_stats(db: AsyncSession = Depends(get_db)):
    """Aggregate stats for the marketplace panel."""
    from pydantic import BaseModel as _BM  # local import to avoid circular
    listings, total = await svc.list_listings(db, active_only=True, page=1, page_size=1000)
    total_calls = sum(l.usage_count for l in listings)
    categories: dict[str, int] = {}
    for l in listings:
        categories[l.category] = categories.get(l.category, 0) + 1
    top_category = max(categories, key=lambda k: categories[k]) if categories else "prediction"
    return {
        "active_models": total,
        "total_calls": total_calls,
        "top_category": top_category,
        "categories": categories,
        "protocol_fee_pct": 15,
    }


@router.get("/models/{slug}")
async def get_model_detail(slug: str, db: AsyncSession = Depends(get_db)):
    """Full detail for a single model listing."""
    listing = await svc.get_listing_by_slug(db, slug)
    if not listing:
        raise HTTPException(404, "Model not found")
    rating_avg = round(listing.rating_sum / listing.rating_count, 2) if listing.rating_count else None
    return {
        **_fmt_listing(listing),
        "approval_status": listing.approval_status,
        "is_verified": listing.is_verified,
        "usage_count": listing.usage_count,
        "rating_avg": rating_avg,
        "rating_count": listing.rating_count,
        "total_staked": str(listing.total_staked),
        "staker_count": listing.staker_count,
        "total_revenue": str(listing.total_revenue),
        "creator_revenue": str(listing.creator_revenue),
        "tags": listing.tags,
    }


class _ModelCallRequest(BaseModel):
    input_data: dict = {}


@router.post("/models/{slug}/call")
async def call_model_endpoint(
    slug: str,
    body: _ModelCallRequest = Body(default_factory=_ModelCallRequest),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invoke a marketplace model; deducts price_per_call from user wallet."""
    listing = await svc.get_listing_by_slug(db, slug)
    if not listing or not listing.is_active:
        raise HTTPException(404, "Model not found or not active")
    if listing.approval_status != "approved":
        raise HTTPException(400, "Model is not yet approved for public use")
    try:
        result = await svc.call_model(db, listing=listing, user=current_user, input_data=body.input_data)
        return result
    except Exception as exc:
        logger.warning("[marketplace] call_model error slug=%s: %s", slug, exc)
        raise HTTPException(500, f"Model call failed: {exc}") from exc
