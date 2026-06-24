"""Real Dropbox provider for Tachyon fragment storage.

Requires ``DROPBOX_ACCESS_TOKEN`` (or a refresh-token trio:
``DROPBOX_APP_KEY``, ``DROPBOX_APP_SECRET``, ``DROPBOX_REFRESH_TOKEN``).

Fragments are stored under ``/tachyon/<name>`` in the Dropbox account.
All blocking SDK calls are run in a thread pool via asyncio.to_thread.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
from typing import Optional

from tachyon.providers.base import CloudProvider

logger = logging.getLogger(__name__)

_FOLDER = "/tachyon"


class DropboxProvider(CloudProvider):
    """Dropbox fragment store using the official Dropbox SDK."""

    def __init__(self, account_id: str, access_token: str | None = None, app_key: str | None = None, app_secret: str | None = None, refresh_token: str | None = None):
        self.account_id = account_id
        self.name = account_id
        self._access_token = (access_token or os.environ.get("DROPBOX_ACCESS_TOKEN", "")).strip()
        self._app_key      = (app_key or os.environ.get("DROPBOX_APP_KEY", "")).strip()
        self._app_secret   = (app_secret or os.environ.get("DROPBOX_APP_SECRET", "")).strip()
        self._refresh_token = (refresh_token or os.environ.get("DROPBOX_REFRESH_TOKEN", "")).strip()
        self._dbx = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_client_sync(self):
        import dropbox

        if self._access_token:
            return dropbox.Dropbox(self._access_token)
        if self._refresh_token and self._app_key and self._app_secret:
            return dropbox.Dropbox(
                oauth2_refresh_token=self._refresh_token,
                app_key=self._app_key,
                app_secret=self._app_secret,
            )
        raise RuntimeError(
            "Dropbox: set DROPBOX_ACCESS_TOKEN or "
            "DROPBOX_REFRESH_TOKEN+DROPBOX_APP_KEY+DROPBOX_APP_SECRET"
        )

    async def _get_client(self):
        if self._dbx is None:
            self._dbx = await asyncio.to_thread(self._build_client_sync)
        return self._dbx

    def _upload_sync(self, dbx, name: str, data: bytes) -> bool:
        import dropbox

        path = f"{_FOLDER}/{name}"
        dbx.files_upload(
            data, path,
            mode=dropbox.files.WriteMode("overwrite"),
            mute=True,
        )
        return True

    def _download_sync(self, dbx, name: str) -> bytes:
        path = f"{_FOLDER}/{name}"
        _meta, res = dbx.files_download(path)
        return res.content

    def _quota_sync(self, dbx) -> dict:
        usage = dbx.users_get_space_usage()
        used  = usage.used
        total = usage.allocation.get_individual().allocated if hasattr(usage.allocation, "get_individual") else 2 * 1024 ** 3
        return {"total": total, "used": used}

    # ------------------------------------------------------------------
    # CloudProvider interface
    # ------------------------------------------------------------------

    async def upload_fragment(self, data: bytes, name: str) -> bool:
        try:
            dbx = await self._get_client()
            return await asyncio.to_thread(self._upload_sync, dbx, name, data)
        except Exception as exc:
            logger.error("[dropbox:%s] upload %s failed: %s", self.account_id, name, exc)
            return False

    async def download_fragment(self, name: str) -> bytes:
        try:
            dbx = await self._get_client()
            return await asyncio.to_thread(self._download_sync, dbx, name)
        except Exception as exc:
            logger.error("[dropbox:%s] download %s failed: %s", self.account_id, name, exc)
            return b""

    async def get_quota(self) -> dict:
        try:
            dbx = await self._get_client()
            return await asyncio.to_thread(self._quota_sync, dbx)
        except Exception:
            return {"total": 2 * 1024 ** 3, "used": 0}

    async def get_latency(self) -> float:
        return 85.0
