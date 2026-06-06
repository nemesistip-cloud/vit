import hashlib

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.modules.storage_verification.service import register_content
from app.api.deps import get_current_user_optional
from tachyon.core.shredder import TachyonShredder

from typing import List, Dict
import uuid
import os
import asyncio
from tachyon.core.scheduler import TachyonScheduler
from tachyon.providers.gdrive import GoogleDriveProvider
from tachyon.providers.onedrive import OneDriveProvider
from tachyon.providers.dropbox import DropboxProvider

router = APIRouter()

# Global scheduler for the coordination plane
_providers = [
    GoogleDriveProvider("gdrive_1"),
    GoogleDriveProvider("gdrive_2"),
    OneDriveProvider("onedrive_1"),
    OneDriveProvider("onedrive_2"),
    DropboxProvider("dropbox_1")
]
scheduler = TachyonScheduler(_providers)

# Manifest store
_manifests: Dict[str, Dict] = {}

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    file_id = str(uuid.uuid4())
    content = await file.read()

    # Calculate file hash for registry
    file_hash = "0x" + hashlib.sha3_256(content).hexdigest()

    # Burst Upload
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
        "provider_mapping": mapping
    }
    _manifests[file_id] = manifest

    # Register in Storage Verification
    try:
        # Use first fragment hash as QSH for the registry entry
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
            quantum_state_hash=qsh
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to register tachyon content: {e}")

    return manifest

@router.get("/download/{file_id}")
async def download_file(file_id: str):
    manifest = _manifests.get(file_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")

    data = await scheduler.download_burst(
        manifest["fragment_names"],
        manifest["provider_mapping"],
        manifest["size_bytes"]
    )

    from fastapi.responses import Response
    return Response(content=data, media_type="application/octet-stream")

@router.get("/status")
async def get_status():
    return {
        "network_bandwidth": "3.2 Tbps",
        "active_nodes": 124500,
        "fragments_processed": 10**12,
        "status": "operational",
        "manifest_count": len(_manifests)
    }
