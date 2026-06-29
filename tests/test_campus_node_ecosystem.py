import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.network.campus_node import CampusRegistrationRequest
from app.modules.network.campus_rewards import UniversityRewardSplit
from app.modules.network.models import NodeActivity
from app.db.models import User
from app.core.errors import AppError

@pytest.mark.asyncio
async def test_campus_registration_flow():
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    user = MagicMock()
    user.id = 1

    body = CampusRegistrationRequest(
        university_name="VIT University",
        country="Nigeria",
        admin_email="admin@vit.edu",
        server_specs={"cpu": 16, "ram": 64},
        verification_doc_url="https://vit.edu/verify.pdf"
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_res

    from app.modules.network.campus_node import register_campus_node
    response = await register_campus_node(body, db, user)

    assert response["status"] == "pending"
    assert "node_id" in response
    db.add.assert_called_once()

@pytest.mark.asyncio
async def test_campus_activation_admin_with_audit():
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    admin = MagicMock()
    admin.id = 55
    admin.username = "super_admin"

    node_id = "campus_123"
    node_record = NodeActivity(
        node_id=node_id,
        node_name="VIT University",
        node_type="pending_campus",
        activity_type="campus_registration_pending"
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = node_record
    db.execute.return_value = mock_res

    request = MagicMock()
    request.client.host = "127.0.0.1"

    with patch("app.modules.network.campus_node.get_or_create_agent_identity", new_callable=AsyncMock) as mock_id, \
         patch("app.modules.network.campus_node.issue_credential", new_callable=AsyncMock) as mock_cred, \
         patch("app.modules.network.campus_node.write_audit", new_callable=AsyncMock) as mock_audit:

        mock_id.return_value = MagicMock(id="did_123")

        from app.modules.network.campus_node import activate_campus_node
        response = await activate_campus_node(node_id, request, db, admin)

        assert response["status"] == "active"
        # Since we now add a NEW record, node_record itself might not be changed if it was from DB,
        # but db.add is called with the new activity.
        db.add.assert_called()
        mock_cred.assert_called_once()
        mock_audit.assert_called_once()
        # Verify admin_id passed to audit
        args, kwargs = mock_audit.call_args
        assert kwargs["admin_id"] == 55

@pytest.mark.asyncio
async def test_university_reward_split_idempotent_with_history():
    db = MagicMock(spec=AsyncSession)
    # mock context manager
    db.begin.return_value.__aenter__ = AsyncMock()
    db.begin.return_value.__aexit__ = AsyncMock()

    db.execute = AsyncMock()
    db.flush = AsyncMock()

    campus_node_id = "campus_123"
    epoch_id = "epoch_2024_01"
    reward_amount = Decimal("100.0")

    node = NodeActivity(
        node_id=campus_node_id,
        node_name="VIT Uni",
        node_type="campus",
        activity_meta={"owner_user_id": 10}
    )

    pool_user = User(id=99, username="university_scholarship_pool")

    wallet_op = MagicMock(id="wallet_op")
    wallet_pool = MagicMock(id="wallet_pool")

    with patch("app.modules.network.campus_rewards.WalletService") as MockWS:
        ws_inst = MockWS.return_value
        ws_inst.get_or_create_wallet = AsyncMock()
        ws_inst.get_or_create_wallet.side_effect = [wallet_op, wallet_pool]
        ws_inst.credit = AsyncMock()

        mock_res_node = MagicMock()
        mock_res_node.scalar_one_or_none.return_value = node

        mock_res_pool = MagicMock()
        mock_res_pool.scalar_one_or_none.return_value = pool_user

        db.execute.side_effect = [mock_res_node, mock_res_pool]

        distributor = UniversityRewardSplit()
        result = await distributor.distribute(db, campus_node_id, epoch_id, reward_amount)

        assert result["operator_share"] == Decimal("70.0")
        assert result["pool_share"] == Decimal("30.0")

        # Verify credits with idempotent references
        assert ws_inst.credit.call_count == 2
        calls = ws_inst.credit.call_args_list
        # Call 1 (Operator)
        assert calls[0].kwargs["reference"] == f"CAMPUS_REWARD:{campus_node_id}:{epoch_id}:OP"
        # Call 2 (Pool)
        assert calls[1].kwargs["reference"] == f"CAMPUS_REWARD:{campus_node_id}:{epoch_id}:POOL"
