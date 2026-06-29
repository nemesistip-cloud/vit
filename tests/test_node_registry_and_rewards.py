import pytest
import httpx
from decimal import Decimal
from unittest.mock import MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.network.node_types import NODE_TYPES
from app.modules.network.capabilities import CapabilityReporter
from app.modules.network.rewards_matrix import RewardsMatrix
from app.modules.network.models import NodeActivity
from app.core.errors import AppError

@pytest.mark.asyncio
async def test_node_types_registry():
    assert "storage" in NODE_TYPES
    assert NODE_TYPES["storage"]["reward_multiplier"] == 1.0
    assert "gpu" in NODE_TYPES
    assert NODE_TYPES["gpu"]["reward_multiplier"] == 5.0
    assert "android" in NODE_TYPES
    assert NODE_TYPES["android"]["min_storage_gb"] == 1

@pytest.mark.asyncio
async def test_capability_reporter_success():
    reporter = CapabilityReporter(base_url="http://test-api")
    node_id = "test-node"
    caps = {"storage_gb": 10.0, "os": "linux"}

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        result = await reporter.report(node_id, caps)
        assert result is True
        mock_post.assert_called_once()

@pytest.mark.asyncio
async def test_capability_reporter_failure():
    reporter = CapabilityReporter(base_url="http://test-api")
    node_id = "test-node"

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=500, text="Internal Server Error")
        result = await reporter.report(node_id, {})
        assert result is False

@pytest.mark.asyncio
async def test_rewards_matrix_calculate_success():
    db = MagicMock(spec=AsyncSession)
    matrix = RewardsMatrix()
    node_id = "node-123"

    # Mock database response for node_type
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = "validator"
    db.execute.return_value = mock_result

    # Case 1: 100% success rate (multiplier 2.0, perf factor 1.5)
    # Total = 10 * 2.0 * 1.5 = 30.0
    reward = await matrix.calculate(db, node_id, {"success_rate": 1.0})
    assert reward == Decimal("30.00000000")

    # Case 2: 0% success rate (multiplier 2.0, perf factor 0.5)
    # Total = 10 * 2.0 * 0.5 = 10.0
    reward = await matrix.calculate(db, node_id, {"success_rate": 0.0})
    assert reward == Decimal("10.00000000")

@pytest.mark.asyncio
async def test_rewards_matrix_node_not_found():
    db = MagicMock(spec=AsyncSession)
    matrix = RewardsMatrix()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result

    with pytest.raises(AppError) as exc:
        await matrix.calculate(db, "unknown-node", {})
    assert exc.value.status_code == 404
    assert exc.value.code == "node_not_found"

@pytest.mark.asyncio
async def test_rewards_matrix_invalid_type():
    db = MagicMock(spec=AsyncSession)
    matrix = RewardsMatrix()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = "unsupported-type"
    db.execute.return_value = mock_result

    with pytest.raises(AppError) as exc:
        await matrix.calculate(db, "node-123", {})
    assert exc.value.status_code == 400
    assert exc.value.code == "invalid_node_type"
