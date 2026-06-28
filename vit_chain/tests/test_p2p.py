import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from vit_chain.p2p.models import PeerNode
from vit_chain.p2p.registry import PeerRegistry
from vit_chain.p2p.discovery import PeerDiscovery
from vit_chain.p2p.bootstrap import BootstrapManager

@pytest.mark.asyncio
async def test_peer_node_model():
    peer = PeerNode(
        node_id="VIT_TEST_1",
        public_key="04" + "a" * 128,
        ip_address="127.0.0.1",
        ws_port=7765,
        node_type="validator"
    )
    assert peer.ws_url == "ws://127.0.0.1:7765/chain/peer"

    d = peer.to_dict()
    assert d["node_id"] == "VIT_TEST_1"
    assert d["ws_url"] == peer.ws_url

@pytest.mark.asyncio
async def test_peer_registry_score():
    registry = PeerRegistry()

    # Perfect score
    score = registry.calculate_score(ping_ms=10, uptime_pct=100.0, chain_height=100, latest_height=100)
    assert score > 0.9

    # Poor score
    score = registry.calculate_score(ping_ms=1000, uptime_pct=50.0, chain_height=50, latest_height=100)
    assert score < 0.5

@pytest.mark.asyncio
async def test_peer_registry_operations(db_session: AsyncSession):
    registry = PeerRegistry()

    node_id = "VIT_REG_TEST"
    await registry.register(
        db_session,
        node_id=node_id,
        public_key="pubkey",
        ip="1.2.3.4",
        port=7765,
        node_type="storage",
        capabilities={"uptime_pct": 99.0}
    )

    count = await registry.get_peer_count(db_session)
    assert count >= 1

    active = await registry.get_active_peers(db_session)
    assert any(p.node_id == node_id for p in active)

    await registry.mark_seen(db_session, node_id, 50)
    await registry.mark_inactive(db_session, node_id)

    active_after = await registry.get_active_peers(db_session)
    assert not any(p.node_id == node_id for p in active_after)

@pytest.mark.asyncio
async def test_peer_discovery_announce():
    discovery = PeerDiscovery(redis_url="redis://localhost:6379")

    mock_redis = MagicMock()
    mock_redis.hset = AsyncMock(return_value=True)
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.publish = AsyncMock(return_value=1)

    with patch.object(discovery, "_get_redis", return_value=mock_redis):
        await discovery.announce("VIT_NODE", {"ip": "1.1.1.1"})

        mock_redis.hset.assert_called()
        mock_redis.publish.assert_called()

@pytest.mark.asyncio
async def test_bootstrap_manager():
    manager = BootstrapManager()

    mock_peers = [{"node_id": "PEER_1", "ws_url": "ws://..."}]

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_peers
        mock_resp.__aenter__.return_value = mock_resp

        mock_get.return_value = mock_resp

        peers = await manager.get_initial_peers("OUR_NODE")
        assert len(peers) == 1
        assert peers[0]["node_id"] == "PEER_1"
