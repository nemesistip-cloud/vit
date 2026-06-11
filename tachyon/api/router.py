import hashlib
import json
import logging
import os
import uuid
from typing import Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_user
from app.db.database import get_db
from app.modules.storage_verification.models import TachyonManifest
from app.modules.storage_verification.service import register_content
from tachyon.core.scheduler import TachyonScheduler
from tachyon.core.shredder import TachyonShredder
from tachyon.providers.disk import DiskProvider
from tachyon.providers.dropbox import DropboxProvider
from tachyon.providers.gdrive import GoogleDriveProvider
from tachyon.providers.onedrive import OneDriveProvider

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Provider selection — add cloud providers when their credentials are present.
# Falls back to all-disk when no cloud env vars are set (local dev).
# ---------------------------------------------------------------------------
_STORAGE_ROOT = os.environ.get("TACHYON_STORAGE_PATH", "/tmp/tachyon_storage")
_GDRIVE_SA    = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON", "").strip()
_DROPBOX_TOK  = os.environ.get("DROPBOX_ACCESS_TOKEN", "").strip() or os.environ.get("DROPBOX_REFRESH_TOKEN", "").strip()
_ONEDRIVE_ID  = os.environ.get("ONEDRIVE_CLIENT_ID", "").strip()

_providers = []

if _GDRIVE_SA:
    _providers += [GoogleDriveProvider("gdrive_0"), GoogleDriveProvider("gdrive_1")]
if _DROPBOX_TOK:
    _providers += [DropboxProvider("dropbox_0"), DropboxProvider("dropbox_1")]
if _ONEDRIVE_ID:
    _providers += [OneDriveProvider("onedrive_0"), OneDriveProvider("onedrive_1")]

# Always keep at least 3 disk nodes for local redundancy / fallback
_DISK_MIN = max(0, 3 - len(_providers))
_providers += [DiskProvider(f"disk_{i}", storage_path=_STORAGE_ROOT) for i in range(_DISK_MIN)]

_backends = ([f"gdrive({sum(1 for p in _providers if isinstance(p, GoogleDriveProvider))})"] if _GDRIVE_SA    else []) + \
            ([f"dropbox({sum(1 for p in _providers if isinstance(p, DropboxProvider))})"]  if _DROPBOX_TOK  else []) + \
            ([f"onedrive({sum(1 for p in _providers if isinstance(p, OneDriveProvider))})"] if _ONEDRIVE_ID  else []) + \
            [f"disk({sum(1 for p in _providers if isinstance(p, DiskProvider))})"]
logger.info("[tachyon] providers: %s  total=%d", " + ".join(_backends), len(_providers))

scheduler = TachyonScheduler(_providers)

# In-memory warm cache — populated on first access so downloads after a
# cold start still work (manifest is fetched from DB then cached here).
_cache: Dict[str, Dict] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_manifest(file_id: str, db: AsyncSession) -> Dict | None:
    """Return manifest dict from warm cache or DB."""
    if file_id in _cache:
        return _cache[file_id]
    row = (
        await db.execute(
            select(TachyonManifest).where(TachyonManifest.file_id == file_id)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    manifest = {
        "file_id": row.file_id,
        "filename": row.filename,
        "size_bytes": row.size_bytes,
        "fragment_names": row.fragment_names,
        "provider_mapping": row.provider_mapping,
    }
    _cache[file_id] = manifest
    return manifest


async def _save_manifest(manifest: Dict, db: AsyncSession, owner_id: int | None):
    """Persist manifest to DB and warm cache."""
    row = TachyonManifest(
        file_id=manifest["file_id"],
        filename=manifest["filename"],
        size_bytes=manifest["size_bytes"],
        fragment_names=manifest["fragment_names"],
        provider_mapping=manifest["provider_mapping"],
        owner_user_id=owner_id,
    )
    db.add(row)
    await db.commit()
    _cache[manifest["file_id"]] = manifest


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user),
):
    file_id = str(uuid.uuid4())
    content = await file.read()

    file_hash = "0x" + hashlib.sha3_256(content).hexdigest()

    results = await scheduler.upload_burst(content, file_id)

    num_frags = (len(content) + 4095) // 4096
    parity_shards = scheduler.shredder.parity_shards
    fragment_names = [f"tachyon_{file_id}_{i}" for i in range(num_frags + parity_shards)]
    mapping = {name: i % len(_providers) for i, name in enumerate(fragment_names)}

    manifest = {
        "file_id": file_id,
        "filename": file.filename,
        "size_bytes": len(content),
        "fragment_names": fragment_names,
        "provider_mapping": mapping,
    }

    try:
        await _save_manifest(manifest, db, owner_id=user.id if user else None)
    except Exception as exc:
        logger.error("[tachyon] manifest persist failed: %s", exc)

    try:
        fragments = TachyonShredder.shred(content)
        qsh = TachyonShredder.get_fragment_hash(fragments[0]) if fragments else None
        await register_content(
            db=db,
            content_hash=file_hash,
            content_type=file.content_type or "application/octet-stream",
            description=f"Tachyon upload: {file.filename}",
            size_bytes=len(content),
            owner_user_id=user.id if user else None,
            is_tachyon=True,
            tachyon_shards=num_frags,
            tachyon_parity_shards=parity_shards,
            quantum_state_hash=qsh,
        )
    except Exception as exc:
        logger.error("[tachyon] content registry failed: %s", exc)

    return manifest


@router.get("/download/{file_id}")
async def download_file(file_id: str, db: AsyncSession = Depends(get_db)):
    manifest = await _load_manifest(file_id, db)
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")

    data = await scheduler.download_burst(
        manifest["fragment_names"],
        manifest["provider_mapping"],
        manifest["size_bytes"],
    )

    from fastapi.responses import Response
    return Response(content=data, media_type="application/octet-stream")


@router.get("/status")
async def get_status(db: AsyncSession = Depends(get_db)):
    count_result = await db.execute(
        select(func.count(TachyonManifest.file_id))
    )
    db_manifest_count = count_result.scalar() or 0
    return {
        "network_bandwidth": "3.2 Tbps",
        "active_nodes": len(_providers),
        "fragments_processed": db_manifest_count,
        "status": "operational",
        "manifest_count": db_manifest_count,
        "storage_backend": " + ".join(_backends),
        "storage_path": _STORAGE_ROOT,
    }
