import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.api.deps import get_current_admin
from app.services.audit import write_audit
from app.modules.storage_verification.models import TachyonManifest
from tachyon.core.orchestrator import TachyonOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()
orchestrator = TachyonOrchestrator()

@router.get("/health")
async def get_tachyon_health(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    pool_health = await orchestrator.pool.health_check()

    # Aggregated stats
    stmt = select(TachyonManifest)
    result = await db.execute(stmt)
    manifests = result.scalars().all()

    total_stored_bytes = sum(m.size_bytes for m in manifests)
    healthy_count = 0
    degraded_count = 0
    for m in manifests:
        meta = m.provider_mapping.get("_metadata", {})
        if meta.get("status") == "active":
            if meta.get("health_score", 1.0) >= 0.8:
                healthy_count += 1
            else:
                degraded_count += 1

    return {
        "providers": pool_health,
        "manifest_count": len(manifests),
        "total_stored_gb": round(total_stored_bytes / (1024**3), 2),
        "healthy_manifests": healthy_count,
        "degraded_manifests": degraded_count
    }

@router.get("/manifests")
async def list_tachyon_manifests(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(TachyonManifest)
    count_stmt = select(func.count(TachyonManifest.file_id))

    if status:
        filter_clause = TachyonManifest.provider_mapping["_metadata"]["status"].as_string() == status
        stmt = stmt.where(filter_clause)
        count_stmt = count_stmt.where(filter_clause)

    stmt = stmt.offset((page - 1) * limit).limit(limit)

    result = await db.execute(stmt)
    manifests = result.scalars().all()

    total = (await db.execute(count_stmt)).scalar() or 0

    items = []
    for m in manifests:
        meta = m.provider_mapping.get("_metadata", {})
        items.append({
            "file_id": m.file_id,
            "filename": m.filename,
            "size": m.size_bytes,
            "health": meta.get("health_score", 1.0),
            "status": meta.get("status", "active"),
            "created_at": m.created_at
        })

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": items
    }

@router.post("/verify/{file_id}")
async def manual_verify_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    try:
        result = await orchestrator.verify(db, file_id)
        await write_audit(
            db=db,
            admin_id=admin.id,
            action="tachyon.verify",
            target_type="manifest",
            target_id=file_id,
            after=result
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/stats")
async def get_tachyon_stats(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(TachyonManifest)
    result = await db.execute(stmt)
    manifests = result.scalars().all()

    total_stored_bytes = sum(m.size_bytes for m in manifests)

    # Shard distribution
    provider_distribution = {}
    for m in manifests:
        shards = m.provider_mapping.get("shards", [])
        for s in shards:
            pid = s.get("provider_id")
            provider_distribution[pid] = provider_distribution.get(pid, 0) + 1

    # Provider usage
    provider_stats = {}
    for provider in orchestrator.pool.providers:
        usage = await provider.get_usage()
        pid = provider.account_id
        provider_stats[pid] = {
            "used_gb": round(usage.get("used_bytes", 0) / (1024**3), 2),
            "quota_gb": round(usage.get("quota_bytes", 0) / (1024**3), 2),
            "health": await provider.health_check()
        }

    # Top 10 largest files
    sorted_manifests = sorted(manifests, key=lambda x: x.size_bytes, reverse=True)
    top_10 = [{
        "file_id": m.file_id,
        "size_gb": round(m.size_bytes / (1024**3), 4)
    } for m in sorted_manifests[:10]]

    return {
        "total_stored_bytes": total_stored_bytes,
        "shard_distribution": provider_distribution,
        "provider_stats": provider_stats,
        "top_10_largest_files": top_10,
        "healing_queue_length": len([m for m in manifests if m.provider_mapping.get("_metadata", {}).get("health_score", 1.0) < 0.8])
    }
