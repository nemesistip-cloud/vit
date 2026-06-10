"""VIT Network API routes — agent/node registry and network growth stats.

Endpoints:
  GET  /api/network/stats           — overall network health and growth
  GET  /api/network/nodes           — registered node list (agents + validators)
  GET  /api/network/nodes/{node_id} — single node activity history
  GET  /api/network/growth          — time-series growth data (last 24h)
  POST /api/network/activity        — internal: record a node activity (used by agents)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.deps import get_current_admin
from app.modules.network.models import NodeActivity, NetworkSnapshot
from app.modules.storage_verification.service import get_storage_stats

router = APIRouter(prefix="/api/network", tags=["VIT Network"])
logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Schemas ─────────────────────────────────────────────────────────────────

class NodeActivityRequest(BaseModel):
    node_id: str
    node_name: str
    node_type: str
    activity_type: str
    contribution_score: float = 1.0
    metadata: Optional[dict] = None


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/stats")
@router.get("/health")
async def network_stats(db: AsyncSession = Depends(get_db)):
    """Overall network health snapshot."""
    now = _utcnow()
    since_24h = now - timedelta(hours=24)
    since_1h = now - timedelta(hours=1)

    # Total unique nodes ever
    total_nodes_res = await db.execute(
        select(func.count(func.distinct(NodeActivity.node_id)))
    )
    total_nodes = total_nodes_res.scalar() or 0

    # Active nodes (had activity in last hour)
    active_nodes_res = await db.execute(
        select(func.count(func.distinct(NodeActivity.node_id))).where(
            NodeActivity.recorded_at >= since_1h
        )
    )
    active_nodes = active_nodes_res.scalar() or 0

    # Total contributions in 24h
    contrib_24h_res = await db.execute(
        select(func.count(NodeActivity.id)).where(
            NodeActivity.recorded_at >= since_24h
        )
    )
    contrib_24h = contrib_24h_res.scalar() or 0

    # Total contributions all-time
    total_contrib_res = await db.execute(select(func.count(NodeActivity.id)))
    total_contrib = total_contrib_res.scalar() or 0

    # Oracle submissions (24h)
    oracle_res = await db.execute(
        select(func.count(NodeActivity.id)).where(
            NodeActivity.activity_type == "oracle_submit",
            NodeActivity.recorded_at >= since_24h,
        )
    )
    oracle_count = oracle_res.scalar() or 0

    # Per-type breakdown (24h)
    type_res = await db.execute(
        select(NodeActivity.activity_type, func.count(NodeActivity.id))
        .where(NodeActivity.recorded_at >= since_24h)
        .group_by(NodeActivity.activity_type)
    )
    type_breakdown = {row[0]: row[1] for row in type_res.all()}

    # Network health score (0–100): active/total nodes * 100 capped
    health_score = round(min(100.0, (active_nodes / max(total_nodes, 1)) * 100), 1)
    # Boost by activity: each 10 contributions in 24h = +1 to health (cap at 100)
    health_score = min(100.0, health_score + contrib_24h / 10)

    # Latest snapshot
    snap_res = await db.execute(
        select(NetworkSnapshot).order_by(NetworkSnapshot.snapshot_at.desc()).limit(1)
    )
    latest_snap = snap_res.scalar_one_or_none()
    prev_contrib = latest_snap.total_contributions if latest_snap else 0
    growth_rate = round(
        ((total_contrib - prev_contrib) / max(prev_contrib, 1)) * 100, 2
    ) if prev_contrib else 0.0

    storage_stats = {}
    try:
        storage_stats = await get_storage_stats(db)
    except Exception as e:
        logger.error(f"Failed to fetch storage stats: {e}")

    return {
        "total_nodes": total_nodes,
        "active_nodes": active_nodes,
        "total_contributions": total_contrib,
        "contributions_24h": contrib_24h,
        "oracle_submissions_24h": oracle_count,
        "network_health_score": round(health_score, 1),
        "growth_rate_24h_pct": growth_rate,
        "activity_breakdown_24h": type_breakdown,
        "storage_stats": storage_stats,
        "snapshot_at": now.isoformat(),
    }


@router.get("/nodes")
async def list_nodes(
    node_type: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all known nodes with contribution stats."""
    now = _utcnow()
    since_24h = now - timedelta(hours=24)
    since_1h = now - timedelta(hours=1)

    # Get all unique nodes from activity log
    q = select(
        NodeActivity.node_id,
        NodeActivity.node_name,
        NodeActivity.node_type,
        func.count(NodeActivity.id).label("total_contributions"),
        func.max(NodeActivity.recorded_at).label("last_active"),
        func.sum(NodeActivity.contribution_score).label("total_score"),
    ).group_by(
        NodeActivity.node_id, NodeActivity.node_name, NodeActivity.node_type
    )
    if node_type:
        q = q.where(NodeActivity.node_type == node_type)
    q = q.order_by(func.sum(NodeActivity.contribution_score).desc()).limit(limit)

    res = await db.execute(q)
    rows = res.all()

    # Get 24h activity per node
    active_24h_res = await db.execute(
        select(NodeActivity.node_id, func.count(NodeActivity.id))
        .where(NodeActivity.recorded_at >= since_24h)
        .group_by(NodeActivity.node_id)
    )
    active_24h = {row[0]: row[1] for row in active_24h_res.all()}

    # Get 1h activity per node (for online status)
    active_1h_res = await db.execute(
        select(NodeActivity.node_id, func.count(NodeActivity.id))
        .where(NodeActivity.recorded_at >= since_1h)
        .group_by(NodeActivity.node_id)
    )
    online_nodes = {row[0] for row in active_1h_res.all()}

    nodes = []
    for row in rows:
        node_id, node_name, ntype, total, last_active, score = row
        nodes.append({
            "node_id": node_id,
            "node_name": node_name,
            "node_type": ntype,
            "total_contributions": total,
            "contributions_24h": active_24h.get(node_id, 0),
            "total_score": round(float(score or 0), 2),
            "last_active": last_active.isoformat() if last_active else None,
            "online": node_id in online_nodes,
            "status": "online" if node_id in online_nodes else "idle",
        })

    return {"nodes": nodes, "count": len(nodes)}


@router.get("/nodes/{node_id:path}")
async def node_detail(
    node_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Get recent activity history for a specific node."""
    # Decode URL-encoded slashes
    res = await db.execute(
        select(NodeActivity)
        .where(NodeActivity.node_id == node_id)
        .order_by(NodeActivity.recorded_at.desc())
        .limit(limit)
    )
    activities = res.scalars().all()
    if not activities:
        raise HTTPException(404, f"No activity found for node: {node_id}")

    total_res = await db.execute(
        select(func.count(NodeActivity.id), func.sum(NodeActivity.contribution_score))
        .where(NodeActivity.node_id == node_id)
    )
    total_count, total_score = total_res.one()

    return {
        "node_id": node_id,
        "node_name": activities[0].node_name,
        "node_type": activities[0].node_type,
        "total_contributions": total_count,
        "total_score": round(float(total_score or 0), 2),
        "recent_activity": [
            {
                "id": a.id,
                "activity_type": a.activity_type,
                "contribution_score": a.contribution_score,
                "metadata": a.activity_meta,
                "recorded_at": a.recorded_at.isoformat(),
            }
            for a in activities
        ],
    }


@router.get("/growth")
async def growth_timeseries(
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
):
    """Return hourly contribution counts for the last N hours."""
    now = _utcnow()
    buckets = []
    for h in range(hours, 0, -1):
        bucket_start = now - timedelta(hours=h)
        bucket_end = now - timedelta(hours=h - 1)
        res = await db.execute(
            select(func.count(NodeActivity.id)).where(
                NodeActivity.recorded_at >= bucket_start,
                NodeActivity.recorded_at < bucket_end,
            )
        )
        count = res.scalar() or 0
        buckets.append({
            "hour": bucket_start.strftime("%H:00"),
            "timestamp": bucket_start.isoformat(),
            "contributions": count,
        })

    total = sum(b["contributions"] for b in buckets)
    return {"hours": hours, "total": total, "buckets": buckets}


@router.post("/activity")
async def record_activity(
    body: NodeActivityRequest,
    db: AsyncSession = Depends(get_db),
):
    """Internal: agents call this to record a network contribution."""
    record = NodeActivity(
        node_id=body.node_id,
        node_name=body.node_name,
        node_type=body.node_type,
        activity_type=body.activity_type,
        contribution_score=body.contribution_score,
        activity_meta=body.metadata,
    )
    db.add(record)
    await db.commit()
    return {"status": "recorded", "id": record.id}


@router.post("/snapshot", include_in_schema=False)
async def create_snapshot(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Admin: manually trigger a network snapshot."""
    now = _utcnow()
    since_24h = now - timedelta(hours=24)
    since_1h = now - timedelta(hours=1)

    total_n = (await db.execute(select(func.count(func.distinct(NodeActivity.node_id))))).scalar() or 0
    active_n = (await db.execute(
        select(func.count(func.distinct(NodeActivity.node_id))).where(NodeActivity.recorded_at >= since_1h)
    )).scalar() or 0
    total_c = (await db.execute(select(func.count(NodeActivity.id)))).scalar() or 0
    oracle_c = (await db.execute(
        select(func.count(NodeActivity.id)).where(
            NodeActivity.activity_type == "oracle_submit",
            NodeActivity.recorded_at >= since_24h,
        )
    )).scalar() or 0

    health = min(100.0, (active_n / max(total_n, 1)) * 100)

    snap = NetworkSnapshot(
        total_nodes=total_n,
        active_nodes=active_n,
        total_contributions=total_c,
        oracle_submissions=oracle_c,
        network_health_score=round(health, 1),
    )
    db.add(snap)
    await db.commit()
    return {"status": "snapshot_created", "id": snap.id}
