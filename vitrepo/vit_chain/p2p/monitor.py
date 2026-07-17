import asyncio
import time
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from .connection import ConnectionManager
from .registry import PeerRegistry
from .protocol import MessageType, serialize
from .models import PeerNode

logger = logging.getLogger(__name__)

class PeerMonitor:
    PING_INTERVAL = 30  # seconds
    DEAD_THRESHOLD = 3  # missed pings

    def __init__(self, registry: PeerRegistry = None):
        self.registry = registry or PeerRegistry()
        self.missed_pings: dict[str, int] = {}

    async def ping_loop(self, connection_manager: ConnectionManager,
                         db_factory: callable):
        """
        Every PING_INTERVAL seconds:
          Send PING to all connected peers
          Mark peers that don't respond as inactive
          Update scores in registry
          Prune connections below score threshold 0.2
        """
        while True:
            try:
                ping_time = int(time.time() * 1000)
                connected_ids = connection_manager.get_connected_peers()

                # 1. Update missed pings tracking
                current_tracking = set(self.missed_pings.keys())
                for node_id in connected_ids:
                    current_tracking.discard(node_id)

                    # Increment missed pings.
                    # If we got a PONG since last ping, this should have been reset.
                    self.missed_pings[node_id] = self.missed_pings.get(node_id, 0) + 1

                    # 2. Send PING
                    await connection_manager.send_to(node_id, {
                        "type": MessageType.PING,
                        "timestamp": ping_time
                    })

                # Cleanup tracking for disconnected nodes
                for node_id in current_tracking:
                    self.missed_pings.pop(node_id, None)

                # 3. Handle inactive peers
                async with db_factory() as db:
                    for node_id, missed in list(self.missed_pings.items()):
                        if missed >= self.DEAD_THRESHOLD:
                            logger.warning(f"Peer {node_id} missed {missed} pings, marking inactive")
                            await self.registry.mark_inactive(db, node_id)
                            # Close connection if exists
                            if node_id in connection_manager.connections:
                                await connection_manager.connections[node_id].disconnect()
                            self.missed_pings.pop(node_id)
                        else:
                            # 4. Update scores and prune
                            peer = await db.get(PeerNode, node_id) if hasattr(db, 'get') else None
                            if not peer:
                                # Fallback if db.get not available in stub
                                from sqlalchemy import select
                                res = await db.execute(select(PeerNode).where(PeerNode.node_id == node_id))
                                peer = res.scalar_one_or_none()

                            if peer and peer.score < 0.2 and not peer.is_bootstrap:
                                logger.info(f"Pruning low-score peer {node_id} (score: {peer.score})")
                                if node_id in connection_manager.connections:
                                    await connection_manager.connections[node_id].disconnect()

                    await db.commit()
            except Exception as e:
                logger.error(f"Error in PeerMonitor ping loop: {e}")

            await asyncio.sleep(self.PING_INTERVAL)

    async def network_health(self, db: AsyncSession) -> dict:
        """Calculate network health stats."""
        active_count = await self.registry.get_peer_count(db)

        if active_count >= 10:
            health = "healthy"
        elif active_count >= 3:
            health = "degraded"
        else:
            health = "critical"

        return {
            "status": health,
            "active_peers": active_count,
            "timestamp": int(time.time())
        }
