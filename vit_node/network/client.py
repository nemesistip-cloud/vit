import json
import asyncio
import websockets
from app.core.errors import AppError

# TODO: Import from vit_chain.p2p.protocol when 3.2 merges
try:
    from vit_chain.p2p.protocol import P2PProtocol
    PROTOCOL_AVAILABLE = True
except ImportError:
    PROTOCOL_AVAILABLE = False
    class P2PProtocol:
        @staticmethod
        def create_handshake(node_id, key): return {"type": "handshake", "node_id": node_id}
        @staticmethod
        def parse_message(data): return json.loads(data)

class P2PClient:
    def __init__(self):
        self.ws = None
        self.node_id = None

    async def connect(self, peer_url: str,
                       our_node_id: str,
                       our_key: str) -> bool:
        self.node_id = our_node_id
        try:
            self.ws = await websockets.connect(peer_url)

            # Perform handshake
            handshake = P2PProtocol.create_handshake(our_node_id, our_key)
            await self.send(handshake)

            # Wait for handshake response
            response_raw = await self.ws.recv()
            response = P2PProtocol.parse_message(response_raw)

            if response.get("type") == "handshake_ack":
                return True
            return False
        except Exception as e:
            raise AppError(f"Failed to connect to P2P network: {str(e)}", code="p2p_connection_error")

    async def receive_loop(self, gossip_handler: callable):
        if not self.ws:
            raise AppError("P2P client not connected", code="p2p_not_connected")

        try:
            async for message_raw in self.ws:
                message = P2PProtocol.parse_message(message_raw)
                await gossip_handler(message)
        except websockets.ConnectionClosed:
            pass
        except Exception as e:
            raise AppError(f"Error in P2P receive loop: {str(e)}", code="p2p_receive_error")

    async def send(self, message: dict):
        if not self.ws:
            raise AppError("P2P client not connected", code="p2p_not_connected")
        await self.ws.send(json.dumps(message))
