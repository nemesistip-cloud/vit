import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_env
from .registry import PeerRegistry

BOOTSTRAP_NODES = [
    {
        "node_id": "VIT_BOOTSTRAP_1",
        "ws_url": get_env("VIT_BOOTSTRAP_WS_URL", "ws://vit.network:7765/api/chain/peer"),
        "http_url": get_env("VIT_BOOTSTRAP_HTTP_URL", "https://vit.network/api/chain/peers"),
        "is_bootstrap": True
    }
]

class BootstrapManager:
    def __init__(self):
        self.registry = PeerRegistry()

    async def get_initial_peers(self, our_node_id: str) -> list[dict]:
        """Connect to each bootstrap node and request peer list via HTTP."""
        all_peers = []
        async with aiohttp.ClientSession() as session:
            for node in BOOTSTRAP_NODES:
                try:
                    async with session.get(node["http_url"], timeout=10) as resp:
                        if resp.status == 200:
                            peers = await resp.json()
                            if isinstance(peers, list):
                                all_peers.extend(peers)
                except Exception:
                    continue

        # Merge results, deduplicate, exclude our own node_id
        seen_nodes = {our_node_id}
        unique_peers = []
        for p in all_peers:
            if p["node_id"] not in seen_nodes:
                unique_peers.append(p)
                seen_nodes.add(p["node_id"])

        return unique_peers[:20]

    async def serve_peer_list(self, db: AsyncSession,
                               requester_node_id: str) -> list[dict]:
        """Returns our known active peers for bootstrapping new nodes."""
        active_peers = await self.registry.get_active_peers(db, limit=50, exclude=[requester_node_id])
        return [p.to_dict() for p in active_peers]
