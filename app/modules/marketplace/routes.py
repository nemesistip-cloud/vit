from __future__ import annotations
import hashlib
import json
import logging
import os
import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_user, get_current_admin
from app.modules.marketplace.models import AIModelListing
from app.modules.marketplace import service as svc
from app.services.gcs_storage import gcs_storage

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

    upload_id = f"user_{current_user.id}_{uuid.uuid4().hex[:8]}"
    package_dir = os.path.join(_MODELS_DIR, upload_id)
    os.makedirs(package_dir, exist_ok=True)

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
        incoming = [*model_files]
        if model_file: incoming.append(model_file)

        for upload in incoming:
            if not upload.filename: continue
            fname = _safe_upload_name(upload.filename)
            content = await upload.read()
            package_sha.update(content)

            lpath = os.path.join(package_dir, fname)
            with open(lpath, "wb") as f: f.write(content)

            # Sync to GCS
            await gcs_storage.upload_model(lpath, f"{upload_id}/{fname}")
            files_meta.append({"filename": fname, "primary": fname == primary_file})

        gcs_uri = f"gs://{os.getenv('GCS_BUCKET_NAME') or 'vit-models'}/{upload_id}/{primary_file or 'model.pkl'}"

        listing = await svc.create_listing(
            db, creator_id=current_user.id, name=name, description=description,
            category=category, tags=tags, price_per_call=Decimal(str(price_per_call)),
            model_key=model_key, pkl_path=upload_id, pkl_sha256=package_sha.hexdigest(),
            gcs_uri=gcs_uri, webhook_url=webhook_url
        )

        import shutil
        shutil.rmtree(package_dir, ignore_errors=True)
        return {**_fmt_listing(listing), "message": "Model uploaded and synced to GCS."}
    except Exception as e:
        import shutil
        shutil.rmtree(package_dir, ignore_errors=True)
        raise HTTPException(500, str(e))

@router.get("/my-listings")
async def my_listings(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    listings = await svc.my_listings(db, current_user.id)
    return [_fmt_listing(l) for l in listings]
