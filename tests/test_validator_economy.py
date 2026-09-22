from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport
from main import app
from app.db.database import AsyncSessionLocal
from app.modules.blockchain.models import ValidatorProfile
from app.db.models import User
from app.modules.governance.models import GovernanceConfig
from app.modules.governance import service as governance_service
from app.modules.wallet.models import Wallet
from app.modules.blockchain.routes import ValidatorApplyRequest, apply_as_validator

# Uses the module-level AsyncSessionLocal — needs a real migrated database.
pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_validator_metrics_route():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/blockchain/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "active_validators" in data
    assert "total_staked" in data
    assert "circulating_supply" in data

@pytest.mark.asyncio
async def test_active_validators_route():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/blockchain/active")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_me_route_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/blockchain/me")
    # Should be 401 since no token provided
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_validator_apply_uses_governance_min_stake(db_session):
    user = User(
        email="validator-config@example.com",
        username="validator-config",
        hashed_password="hash",
        role="pro",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    db_session.add(
        Wallet(
            user_id=user.id,
            vitcoin_balance=Decimal("500.00"),
            staked_vitcoin_balance=Decimal("0.00"),
            is_frozen=False,
        )
    )
    db_session.add(
        GovernanceConfig(
            key="min_stake_vitcoin",
            value="250",
            data_type="int",
            description="Minimum VITCoin stake to become a validator",
        )
    )
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await apply_as_validator(
            body=ValidatorApplyRequest(stake_amount=200),
            current_user=user,
            db=db_session,
        )

    assert exc.value.status_code == 400
    assert "250" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_default_governance_min_stake_is_5(db_session):
    await governance_service.seed_default_config(db_session)
    cfg = await governance_service.get_config(db_session, "min_stake_vitcoin")

    assert cfg is not None
    assert cfg.value == "5"
