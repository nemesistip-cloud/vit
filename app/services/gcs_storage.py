"""app/services/gcs_storage.py — GCS model sync (Removed).

GCS model sync has been removed in favor of Tachyon VESS.
This module is preserved as a skeleton to avoid breaking legacy script imports.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

# GCS is no longer used for model weights.
GCS_AVAILABLE = False

class GCSStorageClient:
    """Legacy wrapper for GCS operations (Now raising NotImplementedError)."""

    def __init__(self) -> None:
        pass

    async def upload_model(self, path: str, key: str) -> str | None:
        """Upload a local file to GCS (REMOVED)."""
        # TODO: wire to Tachyon upload endpoint
        raise NotImplementedError(
            "GCS model sync removed. Use Tachyon VESS for model weight storage."
        )

    async def download_model(self, key: str, path: str) -> str | None:
        """Download a GCS blob to a local path (REMOVED)."""
        # TODO: wire to Tachyon upload endpoint
        raise NotImplementedError(
            "GCS model sync removed. Use Tachyon VESS for model weight storage."
        )

gcs_storage = GCSStorageClient()
