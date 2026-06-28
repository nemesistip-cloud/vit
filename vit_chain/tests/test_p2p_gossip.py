import pytest
import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from vit_chain.p2p.protocol import serialize, deserialize, validate_message, MessageType
from vit_chain.p2p.connection import PeerConnection, ConnectionManager
from vit_chain.p2p.gossip import GossipHandler
from vit_chain.p2p.sync import ChainSyncer

@pytest.mark.asyncio
async def test_protocol_serialization():
    raw = serialize(MessageType.HANDSHAKE, node_id="NODE_1", public_key="PUB_1",
                    chain_height=0, node_type="validator", capabilities={}, protocol_version="1.0")
    msg = deserialize(raw)
    assert msg["type"] == MessageType.HANDSHAKE
    assert msg["node_id"] == "NODE_1"
    assert validate_message(msg) is True

@pytest.mark.asyncio
async def test_peer_connection_handshake():
    with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # Setup mock handshake_ack response
        ack = serialize(MessageType.HANDSHAKE_ACK, node_id="PEER_1", chain_height=100, accepted=True)
        mock_ws.recv.return_value = ack

        conn = PeerConnection("PEER_1", "ws://localhost:7765", "OUR_NODE", "OUR_KEY")
        success = await conn.connect()

        assert success is True
        assert conn.node_id == "PEER_1"
        assert conn.chain_height == 100
        assert conn.is_connected is True

@pytest.mark.asyncio
async def test_gossip_handler_deduplication():
    cm = MagicMock(spec=ConnectionManager)
    cm.broadcast = AsyncMock()

    handler = GossipHandler(cm)

    tx_data = {"hash": "tx1", "data": "payload"}
    msg = {"type": MessageType.NEW_TRANSACTION, "tx": tx_data}

    # First time: broadcast
    mock_db = AsyncMock(spec=AsyncSession)
    await handler.handle_message(msg, "PEER_1", mock_db)
    cm.broadcast.assert_called_once()

    # Second time: no broadcast
    cm.broadcast.reset_mock()
    await handler.handle_message(msg, "PEER_1", mock_db)
    cm.broadcast.assert_not_called()

@pytest.mark.asyncio
async def test_chain_syncer_check():
    cm = MagicMock(spec=ConnectionManager)
    cm.get_connected_peers.return_value = ["PEER_1", "PEER_2"]

    peer1 = MagicMock()
    peer1.chain_height = 10
    peer2 = MagicMock()
    peer2.chain_height = 20

    cm.connections = {"PEER_1": peer1, "PEER_2": peer2}

    syncer = ChainSyncer()
    best_peer = await syncer.check_sync_needed(MagicMock(), cm)

    assert best_peer == "PEER_2"

@pytest.mark.asyncio
async def test_broadcast_exclude():
    our_node_id = "OUR_NODE"
    cm = ConnectionManager(our_node_id, "OUR_KEY")

    conn1 = MagicMock(spec=PeerConnection)
    conn1.is_connected = True
    conn1.ws = AsyncMock()

    conn2 = MagicMock(spec=PeerConnection)
    conn2.is_connected = True
    conn2.ws = AsyncMock()

    cm.connections = {"PEER_1": conn1, "PEER_2": conn2}

    msg = {"type": "test"}
    await cm.broadcast(msg, exclude="PEER_1")

    conn1.ws.send.assert_not_called()
    conn2.ws.send.assert_called_once()
