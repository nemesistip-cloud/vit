"""app/services/gcs_storage.py — Google Cloud Storage client with graceful fallback.

``GCS_AVAILABLE`` is ``False`` when google-cloud-storage is not installed;
all operations become safe no-ops that log a warning rather than crashing.
"""
from __future__ import annotations

import os
import asyncio
import logging

logger = logging.getLogger(__name__)

try:
    from google.cloud import storage as _gcs_lib
    GCS_AVAILABLE = True
except ImportError:
    _gcs_lib = None          # type: ignore[assignment]
    GCS_AVAILABLE = False
    logger.debug(
        "google-cloud-storage not installed — GCS uploads/downloads disabled. "
        "Install with: pip install google-cloud-storage"
    )


class GCSStorageClient:
    """Async wrapper around GCS blob operations."""

    def __init__(self) -> None:
        self.bucket_name: str | None = os.getenv("GCS_BUCKET_NAME")
        self.project_id:  str | None = os.getenv("GCS_PROJECT_ID")

    # ── Upload ────────────────────────────────────────────────────────────────

    async def upload_model(self, path: str, key: str) -> str | None:
        """Upload a local file to GCS. Returns the gs:// URI or None if unavailable."""
        if not GCS_AVAILABLE:
            logger.warning("GCS unavailable — skipping upload of %s → %s", path, key)
            return None
        if not self.bucket_name:
            logger.warning("GCS_BUCKET_NAME not set — skipping upload of %s", key)
            return None
        return await asyncio.to_thread(self._upload_sync, path, key)

    def _upload_sync(self, path: str, key: str) -> str:
        client = _gcs_lib.Client(project=self.project_id)  # type: ignore[union-attr]
        blob   = client.bucket(self.bucket_name).blob(key)
        blob.upload_from_filename(path)
        uri = f"gs://{self.bucket_name}/{key}"
        logger.info("GCS upload complete: %s → %s", path, uri)
        return uri

    # ── Download ──────────────────────────────────────────────────────────────

    async def download_model(self, key: str, path: str) -> str | None:
        """Download a GCS blob to a local path. Returns path or None if unavailable."""
        if not GCS_AVAILABLE:
            logger.warning("GCS unavailable — skipping download of %s", key)
            return None
        if not self.bucket_name:
            logger.warning("GCS_BUCKET_NAME not set — skipping download of %s", key)
            return None
        return await asyncio.to_thread(self._download_sync, key, path)

    def _download_sync(self, key: str, path: str) -> str:
        client = _gcs_lib.Client(project=self.project_id)  # type: ignore[union-attr]
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        client.bucket(self.bucket_name).blob(key).download_to_filename(path)
        logger.info("GCS download complete: gs://%s/%s → %s", self.bucket_name, key, path)
        return path


gcs_storage = GCSStorageClient()
