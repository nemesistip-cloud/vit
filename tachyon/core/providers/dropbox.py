import logging
import asyncio
import dropbox
from dropbox.files import WriteMode
from app.core.errors import AppError

logger = logging.getLogger(__name__)

class DropboxProvider:
    def __init__(self, account_id: str, credentials: dict):
        self.account_id = account_id
        # credentials can be a dict with access_token
        self.access_token = credentials.get("access_token")
        self._dbx = None

    def _get_client(self):
        if self._dbx is None:
            self._dbx = dropbox.Dropbox(self.access_token)
        return self._dbx

    async def upload_shard(self, shard_id: str, data: bytes, folder_id: str = None) -> str:
        try:
            dbx = self._get_client()
            path = f"/tachyon_shards/{shard_id}"
            res = await asyncio.to_thread(
                dbx.files_upload,
                data,
                path,
                mode=WriteMode('overwrite')
            )
            return res.id
        except Exception as e:
            logger.error(f"Dropbox upload failed: {e}")
            raise AppError(500, f"dropbox_upload_failed: {str(e)}")

    async def download_shard(self, file_id: str) -> bytes:
        try:
            dbx = self._get_client()
            # file_id in Dropbox can be the path or the id
            metadata, response = await asyncio.to_thread(dbx.files_download, file_id)
            return response.content
        except Exception as e:
            logger.error(f"Dropbox download failed: {e}")
            raise AppError(404, "shard_not_found")

    async def delete_shard(self, file_id: str) -> bool:
        try:
            dbx = self._get_client()
            await asyncio.to_thread(dbx.files_delete_v2, file_id)
            return True
        except Exception as e:
            logger.warning(f"Dropbox delete failed for {file_id}: {e}")
            return False

    async def get_usage(self) -> dict:
        try:
            dbx = self._get_client()
            usage = await asyncio.to_thread(dbx.users_get_space_usage)
            used = usage.used
            if usage.allocation.is_individual():
                total = usage.allocation.get_individual().allocated
            else:
                total = usage.allocation.get_team().allocated

            return {
                "used_bytes": used,
                "quota_bytes": total,
                "available_bytes": total - used
            }
        except Exception as e:
            logger.error(f"Dropbox get_usage failed: {e}")
            return {"used_bytes": 0, "quota_bytes": 0, "available_bytes": 0}

    async def health_check(self) -> bool:
        try:
            dbx = self._get_client()
            await asyncio.to_thread(dbx.files_list_folder, "", recursive=False, limit=1)
            return True
        except Exception:
            return False
