import httpx
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Tachyon endpoint defaults to the internal API route if not overridden
PORT = os.getenv("PORT", "5000")
TACHYON_ENDPOINT = os.getenv("TACHYON_ENDPOINT", f"http://localhost:{PORT}/api/tachyon")

class TachyonClient:
    async def upload_bytes(self, content: bytes, filename: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                files = {"file": (filename, content)}
                resp = await client.post(f"{TACHYON_ENDPOINT}/upload", files=files)
                if resp.status_code == 200:
                    return resp.json()["file_id"]
                else:
                    logger.error(f"Upload failed with status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.exception(f"Exception during Tachyon bytes upload: {e}")
        return None

    async def upload_model(self, file_path: str) -> Optional[str]:
        if not os.path.exists(file_path):
            logger.error(f"Upload failed: File not found at {file_path}")
            return None
        try:
            filename = os.path.basename(file_path)
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(file_path, "rb") as f:
                    files = {"file": (filename, f)}
                    resp = await client.post(f"{TACHYON_ENDPOINT}/upload", files=files)
                if resp.status_code == 200:
                    return resp.json()["file_id"]
                else:
                    logger.error(f"Upload failed with status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.exception(f"Exception during Tachyon upload: {e}")
        return None

    async def download_model(self, file_id: str, target_path: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(f"{TACHYON_ENDPOINT}/download/{file_id}")
                if resp.status_code == 200:
                    with open(target_path, "wb") as f:
                        f.write(resp.content)
                    return True
                else:
                    logger.error(f"Download failed with status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.exception(f"Exception during Tachyon download: {e}")
        return False

tachyon_client = TachyonClient()
