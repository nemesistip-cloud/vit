import asyncio
import time
import json
import websockets
import logging
from typing import Dict, List, Optional, Callable
from .protocol import serialize, deserialize, validate_message, MessageType, PROTOCOL_VERSION

logger = logging.getLogger(__name__)

class PeerConnection:
    """Manages a single WebSocket connection to a peer."""
    MAX_RECONNECT_ATTEMPTS = 5

    def __init__(self, node_id: str, ws_url: str,
                 our_node_id: str, our_key: str,
                 node_type: str = "validator",
                 capabilities: dict = None):
        self.node_id = node_id
        self.ws_url = ws_url
        self.our_node_id = our_node_id
        self.our_key = our_key
        self.node_type = node_type
        self.capabilities = capabilities or {}

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._last_ping_time = 0
        self._latency = 0
        self._handshake_complete = False
        self.chain_height = 0

    async def connect(self) -> bool:
        """Connect WebSocket, perform handshake, return success."""
        try:
            self.ws = await websockets.connect(self.ws_url)

            # Initiate handshake
            handshake = serialize(
                MessageType.HANDSHAKE,
                node_id=self.our_node_id,
                public_key=self.our_key,
                chain_height=0,  # Should be actual height
                node_type=self.node_type,
                capabilities=self.capabilities,
                protocol_version=PROTOCOL_VERSION
            )
            await self.ws.send(handshake)

            # Wait for handshake_ack
            response_raw = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
            response = deserialize(response_raw)

            if response.get("type") == MessageType.HANDSHAKE_ACK and response.get("accepted"):
                self._handshake_complete = True
                self.chain_height = response.get("chain_height", 0)
                logger.info(f"Handshake successful with {self.node_id}")
                return True

            await self.disconnect()
            return False
        except Exception as e:
            logger.error(f"Failed to connect to {self.ws_url}: {e}")
            return False

    async def disconnect(self):
        if self.ws:
            await self.ws.close()
            self.ws = None
        self._handshake_complete = False

    async def send(self, message: dict) -> bool:
        """Serialize and send, return False if disconnected."""
        if not self.is_connected:
            return False
        try:
            await self.ws.send(json.dumps(message))
            return True
        except Exception:
            return False

    async def receive_loop(self, handler: Callable, db_factory: Callable):
        """Infinite receive loop, calls handler(msg) for each message."""
        reconnect_attempts = 0
        while reconnect_attempts < self.MAX_RECONNECT_ATTEMPTS:
            if not self.is_connected:
                success = await self.connect()
                if not success:
                    reconnect_attempts += 1
                    await asyncio.sleep(min(2 ** reconnect_attempts, 60))
                    continue
                reconnect_attempts = 0

            try:
                async for message_raw in self.ws:
                    msg = deserialize(message_raw)
                    if validate_message(msg):
                        # Handle PING/PONG internally
                        if msg["type"] == MessageType.PING:
                            await self.ws.send(serialize(MessageType.PONG, timestamp=msg["timestamp"]))
                        elif msg["type"] == MessageType.PONG:
                            self._latency = int((time.time() * 1000) - msg["timestamp"])
                            # Notify handler or monitor if needed to reset missed pings
                            await handler(msg, self.node_id, None) # Pass None for DB if not needed for PONG
                        else:
                            async with db_factory() as db:
                                await handler(msg, self.node_id, db)
            except websockets.ConnectionClosed:
                logger.warning(f"Connection lost to {self.node_id}")
                self.ws = None
            except Exception as e:
                logger.error(f"Error in receive loop for {self.node_id}: {e}")
                await self.disconnect()
                await asyncio.sleep(5)

    @property
    def is_connected(self) -> bool:
        return self.ws is not None and self.ws.open and self._handshake_complete

    @property
    def latency_ms(self) -> int:
        return self._latency

class ConnectionManager:
    """Manages all peer connections for this node."""
    MAX_CONNECTIONS = 20

    def __init__(self, our_node_id: str, our_key: str):
        self.our_node_id = our_node_id
        self.our_key = our_key
        self.connections: Dict[str, PeerConnection] = {}
        self._lock = asyncio.Lock()

    async def connect_to_peers(self, peer_list: list[dict], handler: Callable, db_factory: Callable):
        """Connect to up to MAX_CONNECTIONS peers."""
        async with self._lock:
            # Sort peers: prefer validators/campus nodes
            def peer_priority(p):
                nt = p.get("node_type", "")
                if nt == "validator": return 0
                if nt == "campus": return 1
                return 2

            sorted_peers = sorted(peer_list, key=peer_priority)

            for p in sorted_peers:
                if len(self.connections) >= self.MAX_CONNECTIONS:
                    break

                node_id = p["node_id"]
                if node_id == self.our_node_id or node_id in self.connections:
                    continue

                conn = PeerConnection(
                    node_id=node_id,
                    ws_url=p["ws_url"],
                    our_node_id=self.our_node_id,
                    our_key=self.our_key,
                    node_type="validator", # Defaulting to validator for now
                    capabilities={}
                )

                if await conn.connect():
                    self.connections[node_id] = conn
                    asyncio.create_task(conn.receive_loop(handler, db_factory))

    async def broadcast(self, message: dict, exclude: str = None):
        """Send message to all connected peers."""
        msg_str = json.dumps(message)
        tasks = []
        for node_id, conn in self.connections.items():
            if node_id != exclude and conn.is_connected:
                tasks.append(conn.ws.send(msg_str))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_to(self, node_id: str, message: dict) -> bool:
        """Send to specific peer."""
        conn = self.connections.get(node_id)
        if conn:
            return await conn.send(message)
        return False

    def get_connected_peers(self) -> List[str]:
        return [nid for nid, conn in self.connections.items() if conn.is_connected]

    def connection_count(self) -> int:
        return len(self.get_connected_peers())
