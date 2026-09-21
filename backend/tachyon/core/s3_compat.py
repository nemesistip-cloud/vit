import hmac
import hashlib
import time
import logging
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.modules.wallet.models import PlatformConfig

logger = logging.getLogger(__name__)

async def get_s3_api_key(db: AsyncSession) -> str:
    stmt = select(PlatformConfig).where(PlatformConfig.key == "tachyon_s3_api_key")
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    if not config:
        # Fallback to env or default for dev? Build spec says PlatformConfig.
        from app.config import get_env
        return get_env("TACHYON_S3_API_KEY", "")
    return config.value.get("value")

async def verify_s3_auth(request: Request, db: AsyncSession = Depends(get_db)):
    """
    HMAC-SHA256 of (timestamp + method + path)
    Headers: X-VIT-Timestamp, X-VIT-Key, X-VIT-Signature
    """
    timestamp = request.headers.get("X-VIT-Timestamp")
    api_key_id = request.headers.get("X-VIT-Key")
    signature = request.headers.get("X-VIT-Signature")

    if not all([timestamp, api_key_id, signature]):
        raise HTTPException(status_code=401, detail="Missing S3 auth headers")

    # Replay protection: 5 minute window
    try:
        ts_float = float(timestamp)
        if abs(time.time() - ts_float) > 300:
            raise HTTPException(status_code=401, detail="Timestamp expired")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp")

    secret_key = await get_s3_api_key(db)
    if not secret_key:
        logger.critical("TACHYON_S3_API_KEY not configured in PlatformConfig")
        raise HTTPException(status_code=500, detail="S3 API not configured")

    message = f"{timestamp}{request.method}{request.url.path}"
    expected_sig = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, signature):
        raise HTTPException(status_code=401, detail="Invalid S3 signature")

    return api_key_id

from fastapi import APIRouter, Response, UploadFile, File, Form, Body
from fastapi.responses import StreamingResponse
import io
from tachyon.core.orchestrator import TachyonOrchestrator
from app.modules.storage_verification.models import TachyonManifest

router = APIRouter()
orchestrator = TachyonOrchestrator()

@router.put("/{bucket}/{key}")
async def s3_upload(
    bucket: str,
    key: str,
    file: UploadFile = File(None),
    body: bytes = Body(None),
    db: AsyncSession = Depends(get_db),
    auth=Depends(verify_s3_auth)
):
    file_id = f"{bucket}/{key}"
    data = b""
    if file:
        data = await file.read()
    elif body:
        data = body
    else:
        raise HTTPException(status_code=400, detail="No data provided")

    manifest = await orchestrator.upload(db, file_id, key, data)
    sha256 = manifest.provider_mapping.get("_metadata", {}).get("sha256", "")

    return {
        "file_id": file_id,
        "size_bytes": len(data),
        "etag": sha256[:8]
    }

@router.get("/{bucket}/{key}")
async def s3_download(
    bucket: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    auth=Depends(verify_s3_auth)
):
    file_id = f"{bucket}/{key}"
    try:
        data = await orchestrator.retrieve(db, file_id)
        return Response(content=data, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=404, detail="Object not found")

@router.delete("/{bucket}/{key}")
async def s3_delete(
    bucket: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    auth=Depends(verify_s3_auth)
):
    file_id = f"{bucket}/{key}"
    await orchestrator.delete(db, file_id)
    return Response(status_code=204)

@router.head("/{bucket}/{key}")
async def s3_head(
    bucket: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    auth=Depends(verify_s3_auth)
):
    file_id = f"{bucket}/{key}"
    manifest = await orchestrator.manifests.get(db, file_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="Not found")

    sha256 = manifest.provider_mapping.get("_metadata", {}).get("sha256", "")
    headers = {
        "Content-Length": str(manifest.size_bytes),
        "ETag": sha256[:8],
        "Last-Modified": manifest.created_at.isoformat() if manifest.created_at else ""
    }
    return Response(status_code=200, headers=headers)

@router.get("/{bucket}")
async def s3_list_bucket(
    bucket: str,
    db: AsyncSession = Depends(get_db),
    auth=Depends(verify_s3_auth)
):
    prefix = f"{bucket}/"
    stmt = select(TachyonManifest).where(TachyonManifest.file_id.like(f"{prefix}%"))
    result = await db.execute(stmt)
    manifests = result.scalars().all()

    objects = []
    for m in manifests:
        sha256 = m.provider_mapping.get("_metadata", {}).get("sha256", "")
        objects.append({
            "key": m.file_id.replace(prefix, "", 1),
            "size": m.size_bytes,
            "last_modified": m.created_at.isoformat() if m.created_at else "",
            "etag": sha256[:8]
        })

    return {"objects": objects}
