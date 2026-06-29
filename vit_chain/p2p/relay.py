import logging
from sqlalchemy.ext.asyncio import AsyncSession
from .connection import ConnectionManager
from .protocol import serialize

logger = logging.getLogger(__name__)

class NATRelay:
    """
    Helps nodes behind NAT find each other.
    Server acts as relay ONLY for the initial introduction.
    """
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    async def request_introduction(self, node_a_id: str,
                                    node_b_id: str) -> bool:
        """
        Sends introduction message to node_b via server WebSocket.
        node_b then initiates direct connection to node_a.
        """
        # Node A is requesting to be introduced to Node B
        # We need Node B's connection to send the relay request
        intro_msg = {
            "type": "relay_request",
            "target_node": node_b_id,
            "origin_node": node_a_id,
            "origin_info": {
                # In reality, fetch from PeerRegistry or Connection metadata
                "node_id": node_a_id
            }
        }

        return await self.connection_manager.send_to(node_b_id, intro_msg)

    async def handle_relay_request(self, msg: dict,
                                    from_node: str, db: AsyncSession):
        """
        Called when a node sends type: "relay_request".
        Forwards to target node via their server WebSocket connection.
        """
        target_node = msg.get("target_node")
        if not target_node:
            return

        logger.info(f"Relaying introduction request from {from_node} to {target_node}")

        relay_msg = {
            "type": "relay_intro",
            "from_node": from_node,
            "from_info": msg.get("origin_info", {})
        }

        # Forward to target node
        success = await self.connection_manager.send_to(target_node, relay_msg)

        if success:
            logger.debug(f"Relay successful: {from_node} -> {target_node}")
        else:
            logger.warning(f"Relay failed: {target_node} not connected")
