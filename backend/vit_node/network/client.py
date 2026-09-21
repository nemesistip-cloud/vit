import json
import asyncio
import websockets
import secrets
import time
from app.core.errors import AppError
from vit_chain.p2p.protocol import MessageType, PROTOCOL_VERSION, deserialize, serialize

class P2PClient:
    def __init__(self):
        self.ws = None
        self.node_id = None

    async def connect(self, peer_url: str,
                       our_node_id: str,
                       our_key: str,
                       node_type: str = "storage",
                       capabilities: dict | None = None,
                       chain_height: int = 0,
                       signature: str | None = None,
                       handshake_timestamp: float | None = None,
                       handshake_nonce: str | None = None) -> bool:
        self.node_id = our_node_id
        try:
            self.ws = await websockets.connect(peer_url)

            # Perform handshake
            handshake_fields = dict(
                node_id=our_node_id,
                public_key=our_key,
                chain_height=chain_height,
                node_type=node_type,
                capabilities=capabilities or {},
                protocol_version=PROTOCOL_VERSION,
                timestamp=handshake_timestamp if handshake_timestamp is not None else time.time(),
                nonce=handshake_nonce if handshake_nonce is not None else secrets.token_hex(16),
            )
            if signature:
                handshake_fields["signature"] = signature
            handshake = serialize(MessageType.HANDSHAKE, **handshake_fields)
            await self.ws.send(handshake)

            # Wait for handshake response
            response_raw = await self.ws.recv()
            response = deserialize(response_raw)

            if response.get("type") == MessageType.HANDSHAKE_ACK and response.get("accepted"):
                return True
            return False
        except Exception as e:
            raise AppError(f"Failed to connect to P2P network: {str(e)}", code="p2p_connection_error")

    async def receive_loop(self, gossip_handler: callable):
        if not self.ws:
            raise AppError("P2P client not connected", code="p2p_not_connected")

        try:
            async for message_raw in self.ws:
                message = deserialize(message_raw)
                await gossip_handler(message)
        except websockets.ConnectionClosed:
            pass
        except Exception as e:
            raise AppError(f"Error in P2P receive loop: {str(e)}", code="p2p_receive_error")

    async def send(self, message: dict):
        if not self.ws:
            raise AppError("P2P client not connected", code="p2p_not_connected")
        await self.ws.send(json.dumps(message))
