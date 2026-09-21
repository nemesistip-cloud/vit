import logging
import asyncio
import httpx
import msal
from app.core.errors import AppError

logger = logging.getLogger(__name__)

class OneDriveProvider:
    def __init__(self, account_id: str, credentials: dict):
        self.account_id = account_id
        self.tenant_id = credentials.get("tenant_id")
        self.client_id = credentials.get("client_id")
        self.client_secret = credentials.get("client_secret")
        self._app = None
        self._token = None

    def _get_app(self):
        if self._app is None:
            self._app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}",
                client_credential=self.client_secret,
            )
        return self._app

    async def _get_token(self):
        app = self._get_app()
        result = app.acquire_token_silent(["https://graph.microsoft.com/.default"], account=None)
        if not result:
            result = await asyncio.to_thread(
                app.acquire_token_for_client,
                scopes=["https://graph.microsoft.com/.default"]
            )
        if "access_token" in result:
            return result["access_token"]
        else:
            raise AppError(f"onedrive_auth_failed: {result.get('error_description')}", status_code=500, code="onedrive_auth_failed")

    async def upload_shard(self, shard_id: str, data: bytes, folder_id: str = None) -> str:
        try:
            token = await self._get_token()
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/root:/tachyon_shards/{shard_id}:/content"
            async with httpx.AsyncClient() as client:
                resp = await client.put(
                    url,
                    content=data,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/octet-stream"
                    }
                )
                resp.raise_for_status()
                return resp.json()["id"]
        except Exception as e:
            logger.error(f"OneDrive upload failed: {e}")
            raise AppError(f"onedrive_upload_failed: {str(e)}", status_code=500, code="onedrive_upload_failed")

    async def download_shard(self, file_id: str) -> bytes:
        try:
            token = await self._get_token()
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"}
                )
                if resp.status_code == 404:
                    raise AppError("shard_not_found", status_code=404, code="shard_not_found")
                resp.raise_for_status()
                return resp.content
        except AppError:
            raise
        except Exception as e:
            logger.error(f"OneDrive download failed: {e}")
            raise AppError(f"onedrive_download_failed: {str(e)}", status_code=500, code="onedrive_download_failed")

    async def delete_shard(self, file_id: str) -> bool:
        try:
            token = await self._get_token()
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}"
            async with httpx.AsyncClient() as client:
                resp = await client.delete(
                    url,
                    headers={"Authorization": f"Bearer {token}"}
                )
                return resp.status_code in (200, 204)
        except Exception as e:
            logger.warning(f"OneDrive delete failed for {file_id}: {e}")
            return False

    async def get_usage(self) -> dict:
        try:
            token = await self._get_token()
            url = "https://graph.microsoft.com/v1.0/me/drive"
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"}
                )
                resp.raise_for_status()
                quota = resp.json().get("quota", {})
                used = quota.get("used", 0)
                total = quota.get("total", 0)
                return {
                    "used_bytes": used,
                    "quota_bytes": total,
                    "available_bytes": total - used
                }
        except Exception as e:
            logger.error(f"OneDrive get_usage failed: {e}")
            return {"used_bytes": 0, "quota_bytes": 0, "available_bytes": 0}

    async def health_check(self) -> bool:
        try:
            token = await self._get_token()
            url = "https://graph.microsoft.com/v1.0/me/drive/items/root/children?$top=1"
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"}
                )
                return resp.status_code == 200
        except Exception:
            return False
