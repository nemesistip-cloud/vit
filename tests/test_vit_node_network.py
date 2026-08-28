import json

import pytest
from unittest.mock import AsyncMock, patch

from vit_node.network.client import P2PClient


@pytest.mark.asyncio
async def test_p2p_client_sends_protocol_compliant_handshake():
    websocket = AsyncMock()
    websocket.recv.return_value = json.dumps({
        "type": "handshake_ack",
        "node_id": "PEER_1",
        "chain_height": 3,
        "accepted": True,
    })

    with patch("vit_node.network.client.websockets.connect", new=AsyncMock(return_value=websocket)):
        connected = await P2PClient().connect(
            "ws://peer/chain/peer",
            "NODE_1",
            "04" + "a" * 128,
            node_type="storage",
            capabilities={"storage": True},
            chain_height=2,
        )

    assert connected
    payload = json.loads(websocket.send.call_args.args[0])
    assert payload["type"] == "handshake"
    assert payload["node_id"] == "NODE_1"
    assert payload["public_key"] == "04" + "a" * 128
    assert payload["chain_height"] == 2
    assert payload["node_type"] == "storage"
    assert payload["capabilities"] == {"storage": True}
    assert payload["protocol_version"] == "1.0"
    assert isinstance(payload["timestamp"], float)
    assert len(payload["nonce"]) == 32


@pytest.mark.asyncio
async def test_p2p_client_rejects_unaccepted_handshake():
    websocket = AsyncMock()
    websocket.recv.return_value = json.dumps({
        "type": "handshake_ack",
        "node_id": "PEER_1",
        "chain_height": 3,
        "accepted": False,
    })

    with patch("vit_node.network.client.websockets.connect", new=AsyncMock(return_value=websocket)):
        connected = await P2PClient().connect("ws://peer/chain/peer", "NODE_1", "04" + "a" * 128)

    assert not connected