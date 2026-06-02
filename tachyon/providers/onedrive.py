from tachyon.providers.base import CloudProvider
import asyncio

class OneDriveProvider(CloudProvider):
    """
    Simulated OneDrive Provider for Tachyon Fabric.
    """

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.storage = {}

    async def upload_fragment(self, data: bytes, name: str) -> bool:
        self.storage[name] = data
        await asyncio.sleep(0.01)
        return True

    async def download_fragment(self, name: str) -> bytes:
        await asyncio.sleep(0.01)
        return self.storage.get(name, b"")

    async def get_quota(self) -> dict:
        return {"total": 5*1024**3, "used": 512*1024**2}

    async def get_latency(self) -> float:
        return 65.2
