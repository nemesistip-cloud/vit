import httpx
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Tachyon endpoint defaults to the internal API route if not overridden
TACHYON_ENDPOINT = os.getenv("TACHYON_ENDPOINT", "http://localhost:5000/api/tachyon")

class TachyonClient:
    async def upload_model(self, file_path: str) -> Optional[str]:
        if not os.path.exists(file_path): return None
        try:
            filename = os.path.basename(file_path)
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(file_path, "rb") as f:
                    files = {"file": (filename, f)}
                    resp = await client.post(f"{TACHYON_ENDPOINT}/upload", files=files)
                if resp.status_code == 200:
                    return resp.json()["file_id"]
        except Exception: pass
        return None

    async def download_model(self, file_id: str, target_path: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{TACHYON_ENDPOINT}/download/{file_id}")
                if resp.status_code == 200:
                    with open(target_path, "wb") as f:
                        f.write(resp.content)
                    return True
        except Exception: pass
        return False

tachyon_client = TachyonClient()
