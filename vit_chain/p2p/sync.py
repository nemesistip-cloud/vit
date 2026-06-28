import asyncio
import logging
from typing import List, Optional, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from .protocol import MessageType, serialize
from .connection import ConnectionManager, PeerConnection
from vit_chain.core.blockchain import VITChain, VITBlock

logger = logging.getLogger(__name__)

class ChainSyncer:
    """
    Syncs chain state for a new or behind node.
    Called on startup or when we detect we're behind peers.
    """
    def __init__(self, chain: VITChain = None):
        self.chain = chain or VITChain()
        self._syncing = False
        self._sync_event = asyncio.Event()

    async def check_sync_needed(self, db: AsyncSession,
                                 connection_manager: ConnectionManager) -> Optional[str]:
        """
        Compare our chain_height vs peers' reported heights.
        Return node_id of best peer if we're more than 5 blocks behind.
        """
        our_height = await self.chain.get_height(db)

        best_peer = None
        max_height = our_height

        for node_id in connection_manager.get_connected_peers():
            conn = connection_manager.connections.get(node_id)
            if conn and conn.chain_height > max_height:
                max_height = conn.chain_height
                best_peer = node_id

        if max_height > our_height + 5:
            return best_peer
        return None

    async def sync_from_peer(self, db: AsyncSession,
                               peer_node_id: str,
                               connection_manager: ConnectionManager):
        """
        Send GET_BLOCKS from our height to peer height.
        In batches of 100 blocks.
        """
        if self._syncing:
            return
        self._syncing = True

        try:
            our_height = await self.chain.get_height(db)
            peer_height = connection_manager.connections[peer_node_id].chain_height

            logger.info(f"Starting sync from {peer_node_id} (our height: {our_height}, peer height: {peer_height})")

            current_height = our_height
            while current_height < peer_height:
                start = current_height + 1
                end = min(start + 99, peer_height)

                # Request blocks
                await connection_manager.send_to(peer_node_id, {
                    "type": MessageType.GET_BLOCKS,
                    "from_height": start,
                    "to_height": end
                })

                # Wait for progress (handled by GossipHandler which updates chain height)
                # We wait up to 10 seconds for some progress
                for _ in range(10):
                    await asyncio.sleep(1)
                    new_height = await self.chain.get_height(db)
                    if new_height > current_height:
                        current_height = new_height
                        break
                else:
                    logger.warning(f"Sync stalled at {current_height}")
                    break

                if current_height % 100 == 0 or current_height == peer_height:
                    logger.info(f"Sync progress: {current_height}/{peer_height}")

            logger.info(f"Sync finished at height {current_height}")
        finally:
            self._syncing = False

    async def sync_loop(self, db_factory: Callable,
                         connection_manager: ConnectionManager):
        """Runs every 60 seconds. If sync needed: find best peer and sync."""
        while True:
            try:
                async with db_factory() as db:
                    best_peer = await self.check_sync_needed(db, connection_manager)
                    if best_peer:
                        await self.sync_from_peer(db, best_peer, connection_manager)
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
            await asyncio.sleep(60)
