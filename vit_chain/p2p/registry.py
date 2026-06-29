import datetime
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import PeerNode

class PeerRegistry:
    MAX_PEERS = 50
    PEER_TIMEOUT_SECONDS = 300

    async def register(self, db: AsyncSession,
                        node_id: str,
                        public_key: str,
                        ip: str, port: int,
                        node_type: str,
                        capabilities: dict) -> PeerNode:
        """Upsert peer node in the database."""
        stmt = select(PeerNode).where(PeerNode.node_id == node_id)
        result = await db.execute(stmt)
        peer = result.scalar_one_or_none()

        now = datetime.datetime.now(datetime.timezone.utc)

        if peer:
            peer.public_key = public_key
            peer.ip_address = ip
            peer.ws_port = port
            peer.node_type = node_type
            peer.capabilities = capabilities
            peer.last_seen = now
            peer.is_active = True
        else:
            peer = PeerNode(
                node_id=node_id,
                public_key=public_key,
                ip_address=ip,
                ws_port=port,
                node_type=node_type,
                capabilities=capabilities,
                last_seen=now,
                is_active=True
            )
            db.add(peer)

        await db.flush()
        return peer

    async def get_active_peers(self, db: AsyncSession,
                                 limit: int = 20,
                                 exclude: list[str] = None) -> list[PeerNode]:
        """Returns active peers ordered by score DESC."""
        timeout_threshold = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=self.PEER_TIMEOUT_SECONDS)

        stmt = select(PeerNode).where(
            PeerNode.is_active == True,
            PeerNode.last_seen > timeout_threshold
        )

        if exclude:
            stmt = stmt.where(PeerNode.node_id.notin_(exclude))

        stmt = stmt.order_by(PeerNode.score.desc()).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def mark_seen(self, db: AsyncSession,
                         node_id: str, ping_ms: int):
        """Updates last_seen + last_ping_ms + recalculates score."""
        stmt = select(PeerNode).where(PeerNode.node_id == node_id)
        result = await db.execute(stmt)
        peer = result.scalar_one_or_none()

        if peer:
            peer.last_seen = datetime.datetime.now(datetime.timezone.utc)
            peer.last_ping_ms = ping_ms
            peer.is_active = True

            # Recalculate score (simplified for now as latest_height is needed)
            # We assume latest_height is the max height among known active peers
            latest_height_stmt = select(func.max(PeerNode.chain_height)).where(PeerNode.is_active == True)
            latest_height_res = await db.execute(latest_height_stmt)
            latest_height = latest_height_res.scalar() or 0

            uptime_pct = peer.capabilities.get("uptime_pct", 100.0)
            peer.score = self.calculate_score(ping_ms, uptime_pct, peer.chain_height, latest_height)

            await db.flush()

    async def mark_inactive(self, db: AsyncSession, node_id: str):
        """Marks a node as inactive."""
        stmt = update(PeerNode).where(PeerNode.node_id == node_id).values(is_active=False)
        await db.execute(stmt)
        await db.flush()

    async def get_peer_count(self, db: AsyncSession) -> int:
        """Returns total count of registered peers."""
        stmt = select(func.count(PeerNode.node_id))
        result = await db.execute(stmt)
        return result.scalar() or 0

    def calculate_score(self, ping_ms: int, uptime_pct: float,
                         chain_height: int, latest_height: int) -> float:
        """
        score = (
          0.4 * (1 - min(ping_ms, 1000)/1000) +   (low ping = high score)
          0.3 * uptime_pct/100 +
          0.3 * (1 - abs(chain_height - latest_height)/max(latest_height,1))
        )
        """
        ping_score = 0.4 * (1 - min(ping_ms, 1000) / 1000)
        uptime_score = 0.3 * (uptime_pct / 100.0)

        height_diff = abs(chain_height - latest_height)
        height_denom = max(latest_height, 1)
        height_score = 0.3 * (1 - height_diff / height_denom)

        score = ping_score + uptime_score + height_score
        return round(max(0.0, min(1.0, score)), 4)
