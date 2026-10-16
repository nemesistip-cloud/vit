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
async def test_peer_connection_uses_handshake_signer():
    with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws
        mock_ws.recv.return_value = serialize(
            MessageType.HANDSHAKE_ACK,
            node_id="PEER_1",
            chain_height=100,
            accepted=True,
        )

        signer = MagicMock(return_value="signed-handshake")
        conn = PeerConnection(
            "PEER_1", "ws://localhost:7765", "OUR_NODE", "OUR_KEY",
            handshake_signer=signer,
        )
        assert await conn.connect()
        signer.assert_called_once()
        payload = json.loads(mock_ws.send.call_args.args[0])
        assert payload["signature"] == "signed-handshake"
        assert payload["nonce"]

@pytest.mark.asyncio
async def test_gossip_handler_deduplication():
    cm = MagicMock(spec=ConnectionManager)
    cm.broadcast = AsyncMock()

    handler = GossipHandler(cm)

    tx_data = {"hash": "tx1", "data": "payload"}
    msg = {"type": MessageType.NEW_TRANSACTION, "tx": tx_data}

    # Malformed transaction gossip is dropped without crashing or rebroadcasting.
    mock_db = AsyncMock(spec=AsyncSession)
    await handler.handle_message(msg, "PEER_1", mock_db)
    cm.broadcast.assert_not_called()

    # Repeated malformed payloads remain dropped.
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


@pytest.mark.asyncio
async def test_get_blocks_and_blocks_response_sync():
    cm = MagicMock(spec=ConnectionManager)
    cm.send_to = AsyncMock()
    chain = AsyncMock()
    chain.get_blocks.return_value = [{"height": 0, "block_hash": "hash0"}]
    chain.add_block = AsyncMock(return_value=True)

    handler = GossipHandler(cm, chain=chain)
    mock_db = AsyncMock(spec=AsyncSession)

    # Test GET_BLOCKS routing
    msg_get = {"type": MessageType.GET_BLOCKS, "from_height": 0, "to_height": 10}
    await handler.handle_message(msg_get, "PEER_1", mock_db)
    chain.get_blocks.assert_called_once_with(0, 10, mock_db)
    cm.send_to.assert_called_once_with("PEER_1", {"type": MessageType.BLOCKS_RESPONSE, "blocks": [{"height": 0, "block_hash": "hash0"}]})

@pytest.mark.asyncio
async def test_blocks_response_rejects_corrupted_blocks():
    cm = MagicMock(spec=ConnectionManager)
    chain = AsyncMock()
    chain.add_block = AsyncMock(side_effect=Exception("Invalid block header"))

    handler = GossipHandler(cm, chain=chain)
    mock_db = AsyncMock(spec=AsyncSession)

    corrupted_payload = {"type": MessageType.BLOCKS_RESPONSE, "blocks": [{"invalid": "payload"}]}
    # Processing corrupted block response must not crash or bubble unhandled exception
    await handler.handle_message(corrupted_payload, "PEER_1", mock_db)

@pytest.mark.asyncio
async def test_new_block_gossip_validates_and_persists():
    cm = MagicMock(spec=ConnectionManager)
    cm.broadcast = AsyncMock()
    conn_peer = MagicMock()
    cm.connections = {"PEER_1": conn_peer}

    chain = AsyncMock()
    chain.add_block = AsyncMock(return_value=True)

    handler = GossipHandler(cm, chain=chain)
    mock_db = AsyncMock(spec=AsyncSession)

    # Build a minimal valid block dict
    from vit_chain.crypto.ecdsa import generate_keypair
    from vit_chain.core.block import build_block
    priv, pub = generate_keypair()
    block = build_block(None, [], [], priv, height=0)
    block_dict = block.to_dict()

    msg_block = {"type": MessageType.NEW_BLOCK, "block": block_dict}
    await handler.handle_message(msg_block, "PEER_1", mock_db)

    chain.add_block.assert_called_once()
    cm.broadcast.assert_called_once()
    assert conn_peer.chain_height == 0
