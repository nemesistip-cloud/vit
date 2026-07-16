import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from vit_chain.p2p.router import router
from vit_chain.p2p.relay import NATRelay
from vit_chain.p2p.monitor import PeerMonitor
from vit_chain.p2p.protocol import MessageType, serialize

class AnyDictWithType:
    def __init__(self, type_val):
        self.type_val = type_val
    def __eq__(self, other):
        return isinstance(other, dict) and other.get("type") == self.type_val
    def __repr__(self):
        return f"AnyDictWithType(type_val={self.type_val!r})"

@pytest.fixture
def api_client():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

def test_get_peers_endpoint(api_client):
    with patch("vit_chain.p2p.router._registry.get_active_peers", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        response = api_client.get("/api/chain/peers")
        assert response.status_code == 200
        assert "peers" in response.json()

def test_register_peer_endpoint(api_client):
    with patch("vit_chain.p2p.router._registry.register", new_callable=AsyncMock) as mock_reg:
        mock_reg.return_value = None
        with patch("vit_chain.p2p.router._registry.get_peer_count", new_callable=AsyncMock) as mock_count:
            mock_count.return_value = 5
            with patch("vit_chain.p2p.router.verify_signature", return_value=True):
                payload = {
                    "node_id": "VIT_NEW_NODE",
                    "public_key": "pubkey",
                    "node_type": "validator",
                    "ws_port": 7765,
                    "signature": "valid_sig"
                }
                response = api_client.post("/api/chain/peers/register", json=payload)
                assert response.status_code == 200
                assert response.json()["accepted"] is True
                assert response.json()["peer_count"] == 5

@pytest.mark.asyncio
async def test_nat_relay_logic():
    cm = MagicMock()
    cm.send_to = AsyncMock(return_value=True)

    relay = NATRelay(cm)
    success = await relay.request_introduction("NODE_A", "NODE_B")

    assert success is True
    cm.send_to.assert_called_once()
    args, kwargs = cm.send_to.call_args
    assert args[0] == "NODE_B"
    assert args[1]["type"] == "relay_request"

@pytest.mark.asyncio
async def test_peer_monitor_ping():
    cm = MagicMock()
    cm.get_connected_peers.return_value = ["PEER_1"]
    cm.send_to = AsyncMock(return_value=True)

    def db_factory():
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        return mock_session

    monitor = PeerMonitor()

    with patch("asyncio.sleep", side_effect=[None, Exception("StopLoop")]):
        try:
            await monitor.ping_loop(cm, db_factory)
        except Exception as e:
            if str(e) != "StopLoop":
                raise e

    cm.send_to.assert_called_with("PEER_1", AnyDictWithType(MessageType.PING))
