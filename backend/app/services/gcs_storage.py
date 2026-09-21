"""app/services/gcs_storage.py — VIT Local Model Storage.

GCS has been removed in favour of a simple local filesystem store.
Files are written under {LOCAL_STORAGE_ROOT}/models/ which is suitable
for Replit dev and Render ephemeral-disk deployments.  For persistent
cross-deployment storage, mount a Render Disk at /data and set
LOCAL_STORAGE_ROOT=/data.
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

LOCAL_STORAGE_ROOT = Path(os.getenv("LOCAL_STORAGE_ROOT", "/tmp/vit_storage"))
MODELS_DIR = LOCAL_STORAGE_ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

GCS_AVAILABLE = False  # kept for legacy compat checks


class GCSStorageClient:
    """VIT local filesystem model store (drop-in replacement for GCS)."""

    def __init__(self) -> None:
        pass

    async def upload_model(self, path: str, key: str) -> str | None:
        """Copy a local file into the VIT model store under *key*."""
        src = Path(path)
        if not src.is_file():
            logger.error("[vit-storage] upload_model: source not found: %s", path)
            return None
        dest = MODELS_DIR / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        logger.info("[vit-storage] upload_model: %s → %s", path, dest)
        return str(dest)

    async def download_model(self, key: str, path: str) -> str | None:
        """Copy a file from the VIT model store to *path*."""
        src = MODELS_DIR / key
        if not src.is_file():
            logger.warning("[vit-storage] download_model: key not found: %s", key)
            return None
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        logger.info("[vit-storage] download_model: %s → %s", src, path)
        return path

    def list_models(self) -> list[str]:
        """Return relative paths of all stored model files."""
        if not MODELS_DIR.exists():
            return []
        return [
            str(p.relative_to(MODELS_DIR))
            for p in MODELS_DIR.rglob("*")
            if p.is_file()
        ]


gcs_storage = GCSStorageClient()
