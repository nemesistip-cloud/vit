import os
import aiofiles
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class LocalDiskProvider:
    """
    Local filesystem provider for Tachyon ProviderPool.
    Used for local development, testing, and single-host fallback.
    """

    def __init__(self, account_id: str = "local_disk_0", storage_path: str = "/tmp/tachyon_storage"):
        self.account_id = account_id
        self.storage_path = os.path.join(storage_path, account_id)
        os.makedirs(self.storage_path, exist_ok=True)

    async def upload_shard(self, shard_id: str, data: bytes) -> str:
        file_path = os.path.join(self.storage_path, shard_id)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data)
        return shard_id

    async def download_shard(self, file_id: str) -> bytes:
        file_path = os.path.join(self.storage_path, file_id)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Shard {file_id} not found on local disk")
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    async def delete_shard(self, file_id: str) -> bool:
        file_path = os.path.join(self.storage_path, file_id)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    async def get_usage(self) -> Dict[str, Any]:
        total = 10 * 1024 * 1024 * 1024
        used = 0
        if os.path.exists(self.storage_path):
            for f in os.listdir(self.storage_path):
                fp = os.path.join(self.storage_path, f)
                if os.path.isfile(fp):
                    used += os.path.getsize(fp)
        return {
            "used_bytes": used,
            "quota_bytes": total,
            "available_bytes": max(0, total - used)
        }

    async def health_check(self) -> bool:
        return os.path.exists(self.storage_path) and os.access(self.storage_path, os.W_OK)
