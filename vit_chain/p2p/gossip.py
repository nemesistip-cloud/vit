import logging
import asyncio
from typing import Dict, Any, Optional, Set
from collections import deque
from sqlalchemy.ext.asyncio import AsyncSession
from .protocol import MessageType, serialize
from .connection import ConnectionManager
from vit_chain.core.blockchain import VITChain, VITBlock, VITTransaction, Mempool

logger = logging.getLogger(__name__)

class GossipHandler:
    """
    Handles incoming gossip messages and decides what to forward.
    Anti-duplicate: track seen tx/block hashes, don't re-broadcast.
    """
    SEEN_CACHE_SIZE = 10000

    def __init__(self, connection_manager: ConnectionManager,
                 chain: VITChain = None, mempool: Mempool = None):
        self.connection_manager = connection_manager
        self.chain = chain or VITChain()
        self.mempool = mempool or Mempool()
        self.seen_messages_queue = deque(maxlen=self.SEEN_CACHE_SIZE)
        self.seen_messages_set: Set[str] = set()
        self._seen_lock = asyncio.Lock()

    async def _is_seen(self, msg_id: str) -> bool:
        async with self._seen_lock:
            if msg_id in self.seen_messages_set:
                return True

            if len(self.seen_messages_queue) >= self.SEEN_CACHE_SIZE:
                oldest = self.seen_messages_queue.popleft()
                self.seen_messages_set.discard(oldest)

            self.seen_messages_queue.append(msg_id)
            self.seen_messages_set.add(msg_id)
            return False

    async def handle_message(self, msg: dict,
                              from_node_id: str,
                              db: AsyncSession):
        """Routes to correct handler based on msg["type"]."""
        msg_type = msg.get("type")

        if msg_type == MessageType.NEW_TRANSACTION:
            await self._handle_new_tx(msg["tx"], from_node_id, db)
        elif msg_type == MessageType.NEW_BLOCK:
            await self._handle_new_block(msg["block"], from_node_id, db)
        elif msg_type == MessageType.GET_BLOCKS:
            await self._handle_get_blocks(msg["from_height"], msg["to_height"], from_node_id, db)
        elif msg_type == MessageType.GET_PEERS:
            await self._handle_get_peers(from_node_id, db)
        elif msg_type == MessageType.BLOCKS_RESPONSE:
            await self._handle_blocks_response(msg["blocks"], from_node_id, db)
        elif msg_type == MessageType.HANDSHAKE:
            await self._handle_handshake(msg, from_node_id, db)
        elif msg_type == MessageType.PEERS_RESPONSE:
            # Handle in discovery/connection logic
            pass
        else:
            logger.debug(f"Unhandled message type: {msg_type}")

    async def _handle_handshake(self, msg: dict, from_node: str, db: AsyncSession):
        """Update peer info in DB on handshake."""
        from .registry import PeerRegistry
        registry = PeerRegistry()
        await registry.mark_seen(db, from_node, 0) # Base ping
        # Update chain height in DB
        from .models import PeerNode
        from sqlalchemy import update
        await db.execute(
            update(PeerNode)
            .where(PeerNode.node_id == from_node)
            .values(chain_height=msg.get("chain_height", 0))
        )
        await db.commit()

    async def _handle_new_tx(self, tx_data: dict,
                              from_node: str, db: AsyncSession):
        """Deserialize tx, verify, add to mempool, and forward if new."""
        tx = VITTransaction.deserialize(tx_data)
        tx_hash = tx.get_hash()

        if await self._is_seen(f"tx:{tx_hash}"):
            return

        if tx.verify():
            if self.mempool.add_transaction(tx):
                # Forward to others
                await self.connection_manager.broadcast(
                    {"type": MessageType.NEW_TRANSACTION, "tx": tx_data},
                    exclude=from_node
                )

    async def _handle_new_block(self, block_data: dict,
                                 from_node: str, db: AsyncSession):
        """Deserialize block, validate, add to chain, and forward if new."""
        block = VITBlock.deserialize(block_data)
        block_hash = block.get_hash()

        if await self._is_seen(f"block:{block_hash}"):
            return

        if block.validate():
            await self.chain.add_block(block, db)
            await db.commit()
            # Update peer height in memory
            if from_node in self.connection_manager.connections:
                self.connection_manager.connections[from_node].chain_height = block.height

            # Forward to others
            await self.connection_manager.broadcast(
                {"type": MessageType.NEW_BLOCK, "block": block_data, "height": block.height},
                exclude=from_node
            )

    async def _handle_get_blocks(self, from_height: int,
                                  to_height: int,
                                  from_node: str, db: AsyncSession):
        """Fetch blocks from chain, send BLOCKS_RESPONSE to requester."""
        blocks = await self.chain.get_blocks(from_height, to_height, db)
        await self.connection_manager.send_to(
            from_node,
            {"type": MessageType.BLOCKS_RESPONSE, "blocks": blocks}
        )

    async def _handle_blocks_response(self, blocks_data: list, from_node: str, db: AsyncSession):
        """Process blocks received during sync."""
        for b_data in blocks_data:
            block = VITBlock.deserialize(b_data)
            if block.validate():
                await self.chain.add_block(block, db)
        await db.commit()

    async def _handle_get_peers(self, from_node: str, db: AsyncSession):
        """Send PEERS_RESPONSE to requester."""
        from .registry import PeerRegistry
        registry = PeerRegistry()
        active_peers = await registry.get_active_peers(db, limit=20, exclude=[from_node])
        peers_data = [p.to_dict() for p in active_peers]
        await self.connection_manager.send_to(
            from_node,
            {"type": MessageType.PEERS_RESPONSE, "peers": peers_data}
        )

    async def on_new_local_transaction(self, tx_data: dict):
        """Called when this node creates a transaction."""
        tx_hash = tx_data.get("hash", "local_tx")
        await self._is_seen(f"tx:{tx_hash}")
        await self.connection_manager.broadcast(
            {"type": MessageType.NEW_TRANSACTION, "tx": tx_data}
        )

    async def on_new_local_block(self, block_data: dict):
        """Called when consensus finalizes a block."""
        block_hash = block_data.get("hash", "local_block")
        await self._is_seen(f"block:{block_hash}")
        await self.connection_manager.broadcast(
            {"type": MessageType.NEW_BLOCK, "block": block_data, "height": block_data.get("height", 0)}
        )
