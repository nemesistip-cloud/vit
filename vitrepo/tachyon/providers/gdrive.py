"""Real Google Drive provider for Tachyon fragment storage.

Uses a service account (JSON key) supplied via the
``GDRIVE_SERVICE_ACCOUNT_JSON`` environment variable.  The value may be
either a raw JSON string or a base64-encoded JSON string.

Each provider instance keeps a single shared Drive folder
(``tachyon_fragments``) and a local name→file-ID cache so repeated
downloads after a warm start skip the API search round-trip.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
from typing import Optional

from tachyon.providers.base import CloudProvider

logger = logging.getLogger(__name__)

_FOLDER_NAME = "tachyon_fragments"
_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleDriveProvider(CloudProvider):
    """Google Drive fragment store backed by a service account."""

    def __init__(self, account_id: str, service_account_json: str | None = None):
        self.account_id = account_id
        self.name = account_id
        self._sa_json_raw = service_account_json or os.environ.get(
            "GDRIVE_SERVICE_ACCOUNT_JSON", ""
        )
        self._service = None
        self._folder_id: Optional[str] = None
        self._name_to_id: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Synchronous helpers (run in thread pool via asyncio.to_thread)
    # ------------------------------------------------------------------

    def _parse_credentials(self) -> dict:
        raw = self._sa_json_raw.strip()
        try:
            return json.loads(base64.b64decode(raw).decode("utf-8"))
        except Exception:
            return json.loads(raw)

    def _build_service_sync(self):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        sa_info = self._parse_credentials()
        creds = service_account.Credentials.from_service_account_info(
            sa_info, scopes=_SCOPES
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def _get_or_create_folder_sync(self, service) -> str:
        q = (
            f"name='{_FOLDER_NAME}' "
            "and mimeType='application/vnd.google-apps.folder' "
            "and trashed=false"
        )
        res = service.files().list(q=q, fields="files(id)", pageSize=1).execute()
        files = res.get("files", [])
        if files:
            return files[0]["id"]
        meta = {
            "name": _FOLDER_NAME,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = service.files().create(body=meta, fields="id").execute()
        logger.info("[gdrive:%s] created folder '%s' id=%s", self.account_id, _FOLDER_NAME, folder["id"])
        return folder["id"]

    def _upload_sync(self, service, folder_id: str, name: str, data: bytes) -> str:
        from googleapiclient.http import MediaIoBaseUpload

        meta = {"name": name, "parents": [folder_id]}
        media = MediaIoBaseUpload(
            io.BytesIO(data), mimetype="application/octet-stream", resumable=False
        )
        f = service.files().create(body=meta, media_body=media, fields="id").execute()
        return f["id"]

    def _find_file_sync(self, service, folder_id: str, name: str) -> Optional[str]:
        q = f"name='{name}' and '{folder_id}' in parents and trashed=false"
        res = service.files().list(q=q, fields="files(id)", pageSize=1).execute()
        files = res.get("files", [])
        return files[0]["id"] if files else None

    def _download_sync(self, service, file_id: str) -> bytes:
        return service.files().get_media(fileId=file_id).execute()

    def _quota_sync(self, service) -> dict:
        about = service.about().get(fields="storageQuota").execute()
        sq = about.get("storageQuota", {})
        return {
            "total": int(sq.get("limit", 15 * 1024 ** 3)),
            "used": int(sq.get("usage", 0)),
        }

    # ------------------------------------------------------------------
    # Async helpers
    # ------------------------------------------------------------------

    async def _get_service(self):
        if self._service is None:
            self._service = await asyncio.to_thread(self._build_service_sync)
        return self._service

    async def _get_folder_id(self, service) -> str:
        if self._folder_id is None:
            self._folder_id = await asyncio.to_thread(
                self._get_or_create_folder_sync, service
            )
        return self._folder_id

    # ------------------------------------------------------------------
    # CloudProvider interface
    # ------------------------------------------------------------------

    async def upload_fragment(self, data: bytes, name: str) -> bool:
        try:
            svc = await self._get_service()
            fid = await self._get_folder_id(svc)
            drive_id = await asyncio.to_thread(self._upload_sync, svc, fid, name, data)
            self._name_to_id[name] = drive_id
            return True
        except Exception as exc:
            logger.error("[gdrive:%s] upload %s failed: %s", self.account_id, name, exc)
            return False

    async def download_fragment(self, name: str) -> bytes:
        try:
            svc = await self._get_service()
            drive_id = self._name_to_id.get(name)
            if not drive_id:
                fid = await self._get_folder_id(svc)
                drive_id = await asyncio.to_thread(self._find_file_sync, svc, fid, name)
            if not drive_id:
                logger.warning("[gdrive:%s] fragment not found: %s", self.account_id, name)
                return b""
            data = await asyncio.to_thread(self._download_sync, svc, drive_id)
            self._name_to_id[name] = drive_id
            return data
        except Exception as exc:
            logger.error("[gdrive:%s] download %s failed: %s", self.account_id, name, exc)
            return b""

    async def get_quota(self) -> dict:
        try:
            svc = await self._get_service()
            return await asyncio.to_thread(self._quota_sync, svc)
        except Exception:
            return {"total": 15 * 1024 ** 3, "used": 0}

    async def get_latency(self) -> float:
        return 45.5
