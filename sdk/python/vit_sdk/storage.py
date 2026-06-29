import httpx
import io
from typing import Optional, Any, Dict

class StorageAPI:
    """
    API for Tachyon VESS (Verifiable Elastic Storage Swarm) operations.
    """
    def __init__(self, client):
        self.client = client

    async def upload(self, data: bytes, filename: str) -> str:
        """
        Uploads data to Tachyon and returns the file_id.
        """
        files = {"file": (filename, io.BytesIO(data), "application/octet-stream")}
        # In tachyon/api/router.py: @router.post("/upload")
        # Prefix is /api/tachyon
        resp = await self.client.request("POST", "/api/tachyon/upload", files=files)
        return resp.get("file_id")

    async def download(self, file_id: str) -> bytes:
        """
        Downloads the file content from Tachyon.
        """
        # In tachyon/api/router.py: @router.get("/download/{file_id}")
        # Note: VITClient.request currently expects JSON response.
        # Need to handle raw bytes for download.
        response = await self.client.client.get(f"/api/tachyon/download/{file_id}")
        if response.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"Error {response.status_code}: {response.text}",
                request=response.request,
                response=response
            )
        return response.content

    async def delete(self, file_id: str) -> bool:
        """
        Deletes the file manifest from Tachyon.
        """
        # In tachyon/api/router.py: @router.delete("/manifests/{file_id}")
        resp = await self.client.request("DELETE", f"/api/tachyon/manifests/{file_id}")
        return "deleted" in resp

    async def verify(self, file_id: str) -> dict:
        """
        Manually triggers a proof-of-storage check for a file.
        """
        # In tachyon/api/admin_routes.py: @router.post("/verify/{file_id}")
        # Prefix is /api/tachyon/admin
        resp = await self.client.request("POST", f"/api/tachyon/admin/verify/{file_id}")
        return resp
