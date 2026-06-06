import os
import aiofiles
from tachyon.providers.base import CloudProvider

class DiskProvider(CloudProvider):
    """
    Persistent Disk Provider for Tachyon nodes.
    Stores fragments in a local directory.
    """

    def __init__(self, account_id: str, storage_path: str = "/tmp/tachyon_storage"):
        self.account_id = account_id
        self.storage_path = os.path.join(storage_path, account_id)
        os.makedirs(self.storage_path, exist_ok=True)

    async def upload_fragment(self, data: bytes, name: str) -> bool:
        file_path = os.path.join(self.storage_path, name)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data)
        return True

    async def download_fragment(self, name: str) -> bytes:
        file_path = os.path.join(self.storage_path, name)
        if not os.path.exists(file_path):
            return b""
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    async def get_quota(self) -> dict:
        # Simple simulation: 10GB total
        return {"total": 10*1024**3, "used": 0}

    async def get_latency(self) -> float:
        return 2.5 # Local disk is fast
