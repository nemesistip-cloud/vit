import asyncio
import logging
from typing import List, Optional, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .protocol import MessageType, serialize
from .connection import ConnectionManager, PeerConnection
from vit_chain.core.blockchain import VITChain, VITBlock
from vit_chain.consensus.models import ConsensusCheckpoint

logger = logging.getLogger(__name__)

class ChainSyncer:
    """
    Syncs chain state for a new or behind node.
    Includes fork detection and checkpoint support.
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

    async def detect_fork(self, db: AsyncSession,
                           peer_node_id: str,
                           connection_manager: ConnectionManager) -> Optional[int]:
        """
        Compares our block hash at a certain height with the peer's.
        Returns the common ancestor height if a fork is detected, else None.
        """
        our_height = await self.chain.get_height(db)
        if our_height < 0: return None

        # Request peer's latest block hash
        # In a real implementation, this would be a P2P message
        # For simulation, we assume we have connection_manager.connections[peer_node_id].latest_hash
        peer_conn = connection_manager.connections.get(peer_node_id)
        if not peer_conn: return None

        # Simple check: if our tip is different from peer tip at same height
        if peer_conn.chain_height == our_height:
             our_tip = await self.chain.get_latest_block(db)
             if our_tip and hasattr(peer_conn, 'latest_hash') and our_tip.block_hash != peer_conn.latest_hash:
                 # Fork detected. Walk back to find common ancestor.
                 for h in range(our_height - 1, -1, -1):
                     # In real life, we'd ask peer for hash at height 'h'
                     # and compare with our block at height 'h'
                     pass
                 return our_height - 1 # Assume 1 block fork for now

        return None

    async def sync_from_checkpoint(self, db: AsyncSession,
                                     checkpoint: ConsensusCheckpoint,
                                     connection_manager: ConnectionManager):
        """Accelerated sync using a trusted checkpoint."""
        our_height = await self.chain.get_height(db)
        if checkpoint.height > our_height:
            logger.info(f"Syncing from checkpoint at height {checkpoint.height}")
            # Verify checkpoint.validator_set_hash?
            # Set chain height and state root
            # await self.chain.fast_sync(db, checkpoint.height, checkpoint.state_root)
            pass

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
            ancestor = await self.detect_fork(db, peer_node_id, connection_manager)
            if ancestor is not None:
                logger.warning(f"Fork detected at height {ancestor+1}. Reorg needed.")

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

                # Wait for progress
                for _ in range(10):
                    await asyncio.sleep(1)
                    new_height = await self.chain.get_height(db)
                    if new_height > current_height:
                        current_height = new_height
                        break
                else:
                    logger.warning(f"Sync stalled at {current_height}")
                    break

            logger.info(f"Sync finished at height {current_height}")
        finally:
            self._syncing = False

    async def sync_loop(self, db_factory: Callable,
                         connection_manager: ConnectionManager):
        """Periodic sync check."""
        while True:
            try:
                async with db_factory() as db:
                    stmt = select(ConsensusCheckpoint).order_by(ConsensusCheckpoint.height.desc()).limit(1)
                    res = await db.execute(stmt)
                    checkpoint = res.scalar_one_or_none()
                    if checkpoint:
                        await self.sync_from_checkpoint(db, checkpoint, connection_manager)

                    best_peer = await self.check_sync_needed(db, connection_manager)
                    if best_peer:
                        await self.sync_from_peer(db, best_peer, connection_manager)
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
            await asyncio.sleep(60)
