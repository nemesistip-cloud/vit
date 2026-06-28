import io
import logging
import asyncio
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2 import service_account
from app.core.errors import AppError

logger = logging.getLogger(__name__)

class GoogleDriveProvider:
    def __init__(self, account_id: str, credentials: dict):
        self.account_id = account_id
        self.credentials = credentials
        self._service = None
        self._folder_id = None

    def _get_service(self):
        if self._service is None:
            if "type" in self.credentials and self.credentials["type"] == "service_account":
                creds = service_account.Credentials.from_service_account_info(
                    self.credentials,
                    scopes=["https://www.googleapis.com/auth/drive.file"]
                )
            else:
                # Assume OAuth token dict for personal accounts
                from google.oauth2.credentials import Credentials as OAuthCredentials
                creds = OAuthCredentials.from_authorized_user_info(
                    self.credentials,
                    scopes=["https://www.googleapis.com/auth/drive.file"]
                )
            self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    async def _get_folder_id(self) -> str:
        if self._folder_id is not None:
            return self._folder_id

        service = self._get_service()
        query = "name = 'tachyon_shards' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"

        def _list():
            return service.files().list(q=query, fields="files(id)").execute()

        results = await asyncio.to_thread(_list)
        files = results.get("files", [])

        if files:
            self._folder_id = files[0]["id"]
        else:
            file_metadata = {
                "name": "tachyon_shards",
                "mimeType": "application/vnd.google-apps.folder"
            }

            def _create():
                return service.files().create(body=file_metadata, fields="id").execute()

            folder = await asyncio.to_thread(_create)
            self._folder_id = folder.get("id")

        return self._folder_id

    async def upload_shard(self, shard_id: str, data: bytes, folder_id: str = None) -> str:
        try:
            service = self._get_service()
            if folder_id is None:
                folder_id = await self._get_folder_id()

            file_metadata = {
                "name": shard_id,
                "parents": [folder_id]
            }

            media = MediaIoBaseUpload(
                io.BytesIO(data),
                mimetype="application/octet-stream",
                resumable=len(data) > 5 * 1024 * 1024
            )

            def _upload():
                return service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields="id"
                ).execute()

            file = await asyncio.to_thread(_upload)
            return file.get("id")
        except Exception as e:
            logger.error(f"Gdrive upload failed: {e}")
            raise AppError(f"gdrive_upload_failed: {str(e)}", status_code=500, code="gdrive_upload_failed")

    async def download_shard(self, file_id: str) -> bytes:
        try:
            service = self._get_service()

            def _download():
                request = service.files().get_media(fileId=file_id)
                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                return file_content.getvalue()

            return await asyncio.to_thread(_download)
        except Exception as e:
            logger.error(f"Gdrive download failed: {e}")
            raise AppError("shard_not_found", status_code=404, code="shard_not_found")

    async def delete_shard(self, file_id: str) -> bool:
        try:
            service = self._get_service()

            def _delete():
                return service.files().delete(fileId=file_id).execute()

            await asyncio.to_thread(_delete)
            return True
        except Exception as e:
            logger.warning(f"Gdrive delete failed for {file_id}: {e}")
            return False

    async def get_usage(self) -> dict:
        try:
            service = self._get_service()

            def _get_about():
                return service.about().get(fields="storageQuota").execute()

            about = await asyncio.to_thread(_get_about)
            quota = about.get("storageQuota", {})
            limit = int(quota.get("limit", 0))
            usage = int(quota.get("usage", 0))
            return {
                "used_bytes": usage,
                "quota_bytes": limit,
                "available_bytes": limit - usage
            }
        except Exception as e:
            logger.error(f"Gdrive get_usage failed: {e}")
            return {"used_bytes": 0, "quota_bytes": 0, "available_bytes": 0}

    async def health_check(self) -> bool:
        try:
            service = self._get_service()

            def _list():
                return service.files().list(pageSize=1).execute()

            await asyncio.to_thread(_list)
            return True
        except Exception:
            return False
