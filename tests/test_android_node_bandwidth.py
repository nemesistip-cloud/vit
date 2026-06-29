import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.network.android_node import AndroidRegistrationRequest, AndroidHeartbeatRequest
from app.modules.network.bandwidth import BandwidthTracker
from app.modules.network.mobile_relay import MobileRelayCoordinator
from app.modules.network.models import NodeActivity

@pytest.mark.asyncio
async def test_android_registration():
    db = MagicMock(spec=AsyncSession)
    db.commit = AsyncMock()
    user = MagicMock(id=1)

    body = AndroidRegistrationRequest(
        device_model="Pixel 7",
        os_version="Android 14",
        max_storage_gb=5.0
    )

    from app.modules.network.android_node import register_android_node
    response = await register_android_node(body, db, user)

    assert response["status"] == "success"
    assert response["node_type"] == "android"
    assert "android_" in response["node_id"]
    db.add.assert_called_once()

@pytest.mark.asyncio
async def test_android_heartbeat_authorized():
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    user = MagicMock(id=1)

    node_id = "android_123"
    # Mock registration record
    reg_record = NodeActivity(
        node_id=node_id,
        node_name="Pixel 7",
        node_type="android",
        activity_meta={"owner_user_id": 1}
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = reg_record
    db.execute.return_value = mock_res

    body = AndroidHeartbeatRequest(
        node_id=node_id,
        is_charging=True,
        is_on_wifi=True,
        storage_used_gb=1.2
    )

    from app.modules.network.android_node import android_heartbeat
    response = await android_heartbeat(body, db, user)

    assert response["status"] == "online"
    assert response["tasks_available"] is True
    db.add.assert_called_once()

@pytest.mark.asyncio
async def test_bandwidth_tracking():
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    tracker = BandwidthTracker()

    node_id = "android_123"
    epoch = 100
    bytes_relayed = 50 * 1024 * 1024 # 50 MB

    # Test recording
    await tracker.record_relay(db, node_id, bytes_relayed, epoch)
    db.add.assert_called_once()

    # Test aggregation mock
    mock_agg = MagicMock()
    mock_agg.scalar.return_value = 50.0
    db.execute.return_value = mock_agg

    total = await tracker.get_epoch_contribution(db, node_id, epoch)
    assert total == 50

@pytest.mark.asyncio
async def test_mobile_relay_coordinator():
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    coordinator = MobileRelayCoordinator()

    # Mock finding active nodes
    node1 = NodeActivity(
        node_id="android_ok",
        activity_meta={"charge_status": "charging", "wifi_status": "connected"}
    )
    node2 = NodeActivity(
        node_id="android_low_bat",
        activity_meta={"charge_status": "discharging", "wifi_status": "connected"}
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [node1, node2]
    db.execute.return_value = mock_res

    relays = await coordinator.get_available_relays(db)

    assert "android_ok" in relays
    assert "android_low_bat" not in relays
