"""University API — Public listing and stats for verified university nodes."""

from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.network.models import NodeActivity
from app.modules.storage_verification.models import UserStorageNode
from app.core.errors import AppError

router = APIRouter(prefix="/api/network/universities", tags=["Universities"])
logger = logging.getLogger(__name__)

# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/")
async def list_universities(
    db: AsyncSession = Depends(get_db)
):
    """
    GET /api/network/universities
    List of verified university nodes with high-level stats.
    Uses subquery to get only the latest unique campus node activities.
    """
    # Subquery to find the latest record for each campus node_id
    subq = (
        select(
            NodeActivity.node_id,
            func.max(NodeActivity.recorded_at).label("latest_ts")
        )
        .where(NodeActivity.node_type == "campus")
        .group_by(NodeActivity.node_id)
        .subquery()
    )

    # Join back to get full latest records
    stmt = (
        select(NodeActivity)
        .join(subq, (NodeActivity.node_id == subq.c.node_id) & (NodeActivity.recorded_at == subq.c.latest_ts))
    )

    res = await db.execute(stmt)
    nodes = res.scalars().all()

    if not nodes:
        return {"universities": [], "count": 0}

    # 2. Extract owner IDs to batch fetch storage stats
    owner_ids = []
    for node in nodes:
        oid = node.activity_meta.get("owner_user_id") if node.activity_meta else None
        if oid:
            owner_ids.append(oid)

    storage_stats = {}
    if owner_ids:
        # Batch query for storage stats per owner
        stats_stmt = (
            select(
                UserStorageNode.user_id,
                func.sum(UserStorageNode.gb_contributed).label("total_gb"),
                func.sum(UserStorageNode.tsc_earned).label("total_earned")
            )
            .where(UserStorageNode.user_id.in_(owner_ids))
            .group_by(UserStorageNode.user_id)
        )
        stats_res = await db.execute(stats_stmt)
        for row in stats_res.all():
            storage_stats[row.user_id] = {
                "gb": float(row.total_gb or 0.0),
                "earned": float(row.total_earned or 0.0)
            }

    university_list = []
    for node in nodes:
        owner_id = node.activity_meta.get("owner_user_id") if node.activity_meta else None
        stats = storage_stats.get(owner_id, {"gb": 0.0, "earned": 0.0})

        university_list.append({
            "id": node.node_id,
            "university": node.node_name,
            "country": node.activity_meta.get("country") if node.activity_meta else "Unknown",
            "storage_contributed_gb": stats["gb"],
            "uptime_pct": 99.9,
            "vit_earned_total": stats["earned"],
            "active_since": node.recorded_at.isoformat() if node.recorded_at else None
        })

    return {"universities": university_list, "count": len(university_list)}

@router.get("/{node_id}/stats")
async def university_stats(
    node_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    GET /api/network/universities/{node_id}/stats
    Detailed stats for one university node.
    """
    # Use order_by and limit to avoid MultipleResultsFound
    stmt = (
        select(NodeActivity)
        .where(NodeActivity.node_id == node_id, NodeActivity.node_type == "campus")
        .order_by(desc(NodeActivity.recorded_at))
        .limit(1)
    )
    res = await db.execute(stmt)
    node = res.scalar_one_or_none()

    if not node:
        raise AppError(f"University node {node_id} not found", status_code=404, code="not_found")

    # Fetch detailed storage records
    owner_id = node.activity_meta.get("owner_user_id") if node.activity_meta else None
    storage_nodes = []
    if owner_id:
        storage_stmt = select(UserStorageNode).where(UserStorageNode.user_id == owner_id)
        storage_res = await db.execute(storage_stmt)
        storage_nodes = [
            {
                "alias": sn.alias,
                "provider": sn.provider,
                "gb_contributed": float(sn.gb_contributed),
                "gb_used": float(sn.gb_used),
                "reliability_score": float(sn.reliability_score),
                "status": sn.status
            }
            for sn in storage_res.scalars().all()
        ]

    # Aggregate contributions in last 24h
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    contrib_stmt = select(func.count(NodeActivity.id)).where(
        NodeActivity.node_id == node_id,
        NodeActivity.recorded_at >= since_24h
    )
    contrib_res = await db.execute(contrib_stmt)
    contributions_24h = contrib_res.scalar() or 0

    return {
        "node_id": node_id,
        "university": node.node_name,
        "metadata": node.activity_meta,
        "storage_nodes": storage_nodes,
        "performance": {
            "uptime_pct": 99.9,
            "latency_ms": 45,
            "contributions_24h": contributions_24h
        }
    }
