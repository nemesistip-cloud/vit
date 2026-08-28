import os
import time
from fastapi import APIRouter, WebSocket, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any, List
from app.db.database import get_db, AsyncSessionLocal
from .protocol import deserialize, serialize, MessageType, PROTOCOL_VERSION, validate_message, verify_handshake
from .registry import PeerRegistry
from .connection import ConnectionManager, PeerConnection
from .gossip import GossipHandler
from .models import PeerNode

router = APIRouter(prefix="/api/chain", tags=["p2p"])

from .monitor import PeerMonitor

# The server identity is deployment configuration, not a code placeholder.
_connection_manager = ConnectionManager(
    our_node_id=os.getenv("P2P_NODE_ID", "VIT_SERVER"),
    our_key=os.getenv("P2P_PUBLIC_KEY", ""),
)
_monitor = PeerMonitor()
_gossip_handler = GossipHandler(_connection_manager)
_registry = PeerRegistry()
_seen_handshake_nonces: set[str] = set()

@router.websocket("/peer")
async def p2p_websocket_peer(websocket: WebSocket):
    """WebSocket endpoint for incoming peer connections."""
    await handle_peer_websocket(
        websocket,
        _connection_manager,
        _gossip_handler,
        _registry,
        AsyncSessionLocal,
        _seen_handshake_nonces,
    )


async def handle_peer_websocket(
    websocket: WebSocket,
    connection_manager: ConnectionManager,
    gossip_handler: GossipHandler,
    registry: PeerRegistry,
    session_factory,
    seen_handshake_nonces: set[str],
):
    """Serve one authenticated peer using injectable node-local dependencies."""
    await websocket.accept()

    try:
        # 1. Receive Handshake
        raw = await websocket.receive_text()
        msg = deserialize(raw)

        if (
            not validate_message(msg)
            or msg["type"] != MessageType.HANDSHAKE
            or not verify_handshake(msg, seen_handshake_nonces)
        ):
            await websocket.close(code=4000, reason="Invalid handshake")
            return

        node_id = msg["node_id"]

        # 2. Register/Update Peer in Registry
        async with session_factory() as db:
            await registry.register(
                db,
                node_id=node_id,
                public_key=msg["public_key"],
                ip=websocket.client.host if websocket.client else "unknown",
                port=msg.get("ws_port", 7765),
                node_type=msg["node_type"],
                capabilities=msg["capabilities"]
            )
            await db.commit()

        # 3. Send Handshake ACK
        ack = serialize(
            MessageType.HANDSHAKE_ACK,
            node_id=connection_manager.our_node_id,
            chain_height=0, # Should be actual height
            accepted=True
        )
        await websocket.send_text(ack)

        # 4. Handle incoming messages
        async for message_raw in websocket.iter_text():
            msg = deserialize(message_raw)
            if validate_message(msg):
                async with session_factory() as db:
                    await gossip_handler.handle_message(msg, node_id, db)

    except Exception as e:
        print(f"WebSocket error for {websocket.client}: {e}")
    finally:
        # Cleanup
        pass

@router.get("/peers")
async def get_peers(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=50)
):
    """Returns list of known active peers for bootstrapping."""
    peers = await _registry.get_active_peers(db, limit=limit)
    return {
        "peers": [
            {
                "node_id": p.node_id,
                "ws_url": p.ws_url,
                "node_type": p.node_type,
                "chain_height": p.chain_height
            } for p in peers
        ]
    }

from vit_chain.crypto.ecdsa import verify_signature

@router.post("/peers/register")
async def register_peer(
    registration: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Node self-registration endpoint."""
    # Validate signature
    sig = registration.get("signature")
    public_key = registration.get("public_key")
    node_id = registration.get("node_id")

    if not all([sig, public_key, node_id]):
        raise HTTPException(status_code=400, detail="Missing required registration fields")

    # Data to verify: node_id + ws_url + node_type
    message = f"{node_id}:{registration.get('ws_url')}:{registration.get('node_type')}"
    from vit_chain.crypto.hash import sha256_bytes
    if not verify_signature(public_key, sha256_bytes(message.encode()), sig):
        raise HTTPException(status_code=401, detail="Invalid registration signature")

    node_id = registration.get("node_id")
    if not node_id:
        raise HTTPException(status_code=400, detail="Missing node_id")

    await _registry.register(
        db,
        node_id=node_id,
        public_key=registration["public_key"],
        ip=registration.get("ip") or "unknown", # Should ideally be verified
        port=registration.get("ws_port", 7765),
        node_type=registration["node_type"],
        capabilities=registration.get("capabilities", {})
    )
    await db.commit()

    count = await _registry.get_peer_count(db)
    return {"accepted": True, "peer_count": count}

@router.get("/network/stats")
async def get_network_stats(db: AsyncSession = Depends(get_db)):
    """Returns overall network health and distribution statistics."""
    total_peers = await _registry.get_peer_count(db)

    # Active peers count
    active_peers = await _registry.get_active_peers(db, limit=1000)
    active_count = len(active_peers)

    # Geographic distribution
    geo_stmt = select(PeerNode.region, func.count(PeerNode.node_id)).group_by(PeerNode.region)
    geo_res = await db.execute(geo_stmt)
    geo_dist = {row[0] or "unknown": row[1] for row in geo_res.all()}

    # Node type distribution
    type_stmt = select(PeerNode.node_type, func.count(PeerNode.node_id)).group_by(PeerNode.node_type)
    type_res = await db.execute(type_stmt)
    type_dist = {row[0] or "unknown": row[1] for row in type_res.all()}

    # Average latency
    latency_stmt = select(func.avg(PeerNode.last_ping_ms)).where(PeerNode.is_active == True)
    latency_res = await db.execute(latency_stmt)
    avg_latency = float(latency_res.scalar() or 0)

    # Network health
    if active_count >= 10: health = "healthy"
    elif active_count >= 3: health = "degraded"
    else: health = "critical"

    return {
        "total_peers": total_peers,
        "active_peers": active_count,
        "geographic_distribution": geo_dist,
        "node_type_distribution": type_dist,
        "avg_latency_ms": round(avg_latency, 2),
        "network_health": health
    }
