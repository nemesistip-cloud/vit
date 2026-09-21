import httpx
import os
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

# Prefer the explicit endpoint, then derive the compatibility API route from
# the service URL used by Render. Keep localhost as the development fallback.
PORT = os.getenv("PORT", "5000")
_tachyon_url = os.getenv("TACHYON_URL", "").rstrip("/")
TACHYON_ENDPOINT = os.getenv(
    "TACHYON_ENDPOINT",
    f"{_tachyon_url}/api/tachyon" if _tachyon_url else f"http://localhost:{PORT}/api/tachyon",
).rstrip("/")


def _auth_headers() -> dict[str, str]:
    from app.core.service_auth import make_service_headers

    headers = make_service_headers("vitnetwork")
    api_key = os.getenv("VIT_STORAGE_API_KEY") or os.getenv("TACHYON_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    """Perform a storage request with retries only for transient failures."""
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.request(
                    method,
                    f"{TACHYON_ENDPOINT}/{path.lstrip('/')}",
                    headers=_auth_headers(),
                    **kwargs,
                )
            if response.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                return response
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt == 2:
                raise
        await asyncio.sleep(2 ** attempt)
    raise RuntimeError("Storage request failed after retries")


def _file_id(response: httpx.Response) -> Optional[str]:
    if response.status_code != 200:
        logger.error("Storage request failed with status %s", response.status_code)
        return None
    try:
        file_id = response.json().get("file_id")
    except (ValueError, AttributeError):
        logger.error("Storage response was not valid JSON")
        return None
    if not file_id:
        logger.error("Storage response did not include file_id")
        return None
    return str(file_id)

class TachyonClient:
    async def health(self) -> dict:
        """Return the deployed Tachyon status using its supported contract."""
        try:
            response = await _request("GET", "/status")
            if response.status_code != 200:
                return {"status": "degraded", "nodes": {}, "http_status": response.status_code}
            payload = response.json()
            breakdown = payload.get("provider_breakdown", {})
            nodes = {
                name: {"ok": payload.get("status") == "operational", "count": count}
                for name, count in breakdown.items()
            }
            return {
                "status": payload.get("status", "unknown"),
                "nodes": nodes,
                "active_nodes": payload.get("active_nodes", 0),
            }
        except Exception as exc:
            logger.error("Storage health check failed: %s", exc)
            return {"status": "unreachable", "nodes": {}, "error": str(exc)}

    async def gc(self) -> dict:
        """Report GC availability until the storage service exposes a GC API."""
        return {
            "status": "unsupported",
            "freed_bytes": 0,
            "orphans_removed": 0,
            "reason": "Tachyon service does not expose a garbage-collection endpoint",
        }

    async def upload_bytes(self, content: bytes, filename: str) -> Optional[str]:
        try:
            response = await _request("POST", "/upload", files={"file": (filename, content)})
            return _file_id(response)
        except Exception as e:
            logger.error("Storage bytes upload failed: %s", e)
        return None

    async def upload_model(self, file_path: str) -> Optional[str]:
        if not os.path.exists(file_path):
            logger.error(f"Upload failed: File not found at {file_path}")
            return None
        try:
            filename = os.path.basename(file_path)
            with open(file_path, "rb") as file_handle:
                response = await _request(
                    "POST", "/upload", files={"file": (filename, file_handle)}
                )
            return _file_id(response)
        except Exception as e:
            logger.error("Storage model upload failed: %s", e)
        return None

    async def download_model(self, file_id: str, target_path: str) -> bool:
        try:
            response = await _request("GET", f"/download/{file_id}")
            if response.status_code == 200 and response.content:
                with open(target_path, "wb") as file_handle:
                    file_handle.write(response.content)
                return True
            logger.error("Storage download failed with status %s", response.status_code)
        except Exception as e:
            logger.error("Storage model download failed: %s", e)
        return False

tachyon_client = TachyonClient()
