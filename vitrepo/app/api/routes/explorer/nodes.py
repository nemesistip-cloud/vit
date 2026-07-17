"""
Explorer Nodes API — P2P node registry and geographic distribution.
"""
from typing import List, Optional, Dict
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from vit_chain.p2p.models import PeerNode
from app.modules.storage_verification.models import UserStorageNode

router = APIRouter(prefix="/nodes", tags=["Explorer Nodes"])

# ── Static Data ──────────────────────────────────────────────────────────────

# Simplified country code to lat/lng lookup for privacy-preserving map
COUNTRY_COORDS = {
    "NG": {"lat": 9.082, "lng": 8.675},
    "US": {"lat": 37.090, "lng": -95.712},
    "GB": {"lat": 55.378, "lng": -3.436},
    "DE": {"lat": 51.165, "lng": 10.451},
    "KE": {"lat": -0.023, "lng": 37.906},
    "GH": {"lat": 7.946, "lng": -1.023},
    "ZA": {"lat": -30.559, "lng": 22.937},
    "BR": {"lat": -14.235, "lng": -51.925},
    "IN": {"lat": 20.593, "lng": 78.962},
    "CN": {"lat": 35.861, "lng": 104.195},
    "RU": {"lat": 61.524, "lng": 105.318},
}

DEFAULT_COORD = {"lat": 0.0, "lng": 0.0}

# ── Schemas ──────────────────────────────────────────────────────────────────

class NodeSummary(BaseModel):
    node_id: str
    type: Optional[str]
    region: Optional[str]
    score: float
    shards_held: float
    last_seen: Optional[str]
    earnings_total: float

class MapNode(BaseModel):
    lat: float
    lng: float
    node_type: Optional[str]
    node_id: str

# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", response_model=List[NodeSummary])
async def list_nodes(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """List all registered P2P nodes with performance and contribution stats."""
    # Join PeerNode -> User -> UserStorageNode
    # Note: Using subqueries to handle potential 1-to-many or missing records cleanly
    stmt = (
        select(
            PeerNode,
            UserStorageNode.gb_used,
            UserStorageNode.tsc_earned
        )
        .outerjoin(User, User.wallet_address == PeerNode.node_id)
        .outerjoin(UserStorageNode, UserStorageNode.user_id == User.id)
        .order_by(desc(PeerNode.score))
        .limit(limit)
    )

    res = await db.execute(stmt)
    rows = res.all()

    return [
        {
            "node_id": r.PeerNode.node_id,
            "type": r.PeerNode.node_type,
            "region": r.PeerNode.region,
            "score": float(r.PeerNode.score or 0),
            "shards_held": float(r.gb_used or 0),
            "last_seen": r.PeerNode.last_seen.isoformat() if r.PeerNode.last_seen else None,
            "earnings_total": float(r.tsc_earned or 0)
        }
        for r in rows
    ]

@router.get("/map")
async def get_nodes_map(db: AsyncSession = Depends(get_db)):
    """Get geographic distribution of nodes (privacy-preserving)."""
    stmt = select(PeerNode).where(PeerNode.is_active == True)
    res = await db.execute(stmt)
    nodes = res.scalars().all()

    map_nodes = []
    for n in nodes:
        coords = COUNTRY_COORDS.get(n.country_code, DEFAULT_COORD)
        map_nodes.append({
            "lat": coords["lat"],
            "lng": coords["lng"],
            "node_type": n.node_type,
            "node_id": n.node_id
        })

    return {"nodes": map_nodes}
