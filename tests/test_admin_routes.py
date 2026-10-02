import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.api.routes.admin import _safe_config_value, list_matches, list_predictions, router, api_key_usage_stats
from app.api.routes.admin_ops import get_mission_control
from app.api.routes import admin_finance
from app.modules.blockchain import routes as blockchain_routes
from app.db.models import Match, Prediction, User
from app.modules.blockchain.models import MatchSettlement
from app.modules.developer.models import APIKey, APIUsageLog
from app.modules.wallet.admin_routes import platform_revenue
from app.modules.wallet.models import Wallet, WalletTransaction


def test_user_export_route_precedes_user_id_route():
    paths = [route.path for route in router.routes]
    assert paths.index("/admin/users/export") < paths.index("/admin/users/{user_id}")


def test_secret_like_config_values_are_redacted():
    assert _safe_config_value("VIT_API_KEY", "must-not-leak") == {"configured": True}
    assert _safe_config_value("token_launch", {"status": "ACTIVE"}) == {"status": "ACTIVE"}


@pytest.mark.asyncio
async def test_admin_match_listing_uses_kickoff_time(db_session):
    kickoff = datetime(2026, 8, 10, 12, 0, 0)
    db_session.add(
        Match(
            external_id="admin-kickoff-regression",
            home_team="Admin Home",
            away_team="Admin Away",
            league="test_league",
            sport="football",
            kickoff_time=kickoff,
            status="upcoming",
            source="test",
        )
    )
    await db_session.commit()

    result = await list_matches(
        page=1,
        limit=10,
        status=None,
        league=None,
        sport=None,
        date_from=(kickoff - timedelta(minutes=1)).isoformat(),
        date_to=(kickoff + timedelta(minutes=1)).isoformat(),
        db=db_session,
        admin=object(),
    )

    assert result["total"] == 1
    assert result["matches"][0]["match_date"] == kickoff.isoformat()


@pytest.mark.asyncio
async def test_admin_prediction_listing_uses_prediction_timestamp(db_session):
    user = User(email="pred-admin@example.com", username="pred_admin", hashed_password="hash", role="user")
    db_session.add(user)
    await db_session.flush()

    match = Match(
        external_id="pred-admin-match",
        home_team="Home",
        away_team="Away",
        league="league",
        sport="football",
        kickoff_time=datetime.utcnow(),
        status="upcoming",
        source="test",
    )
    db_session.add(match)
    await db_session.flush()

    prediction = Prediction(
        match_id=match.id,
        user_id=user.id,
        home_prob=0.5,
        draw_prob=0.2,
        away_prob=0.3,
        status="READY",
        source="test",
        timestamp=datetime.utcnow(),
    )
    db_session.add(prediction)
    await db_session.commit()

    result = await list_predictions(
        page=1,
        limit=10,
        user_id=user.id,
        match_id=match.id,
        was_correct=None,
        date_from=None,
        date_to=None,
        db=db_session,
        admin=object(),
    )

    assert result["total"] == 1
    assert result["predictions"][0]["match_id"] == match.id


@pytest.mark.asyncio
async def test_admin_mission_control_and_platform_revenue_use_live_schema(db_session):
    user = User(email="ops-admin@example.com", username="ops_admin", hashed_password="hash", role="super_admin")
    db_session.add(user)
    await db_session.flush()

    wallet = Wallet(id="wallet-ops", user_id=user.id, vitcoin_balance=Decimal("25.5"))
    db_session.add(wallet)

    tx = WalletTransaction(
        id="tx-ops-1",
        user_id=user.id,
        wallet_id=wallet.id,
        type="deposit",
        currency="USD",
        amount=Decimal("10.00"),
        direction="credit",
        status="confirmed",
        description="deposit",
        reference="ref-ops-1",
        created_at=datetime.utcnow(),
    )
    db_session.add(tx)

    match = Match(
        external_id="mission-control-match",
        home_team="Alpha",
        away_team="Beta",
        league="league",
        sport="football",
        kickoff_time=datetime.utcnow() + timedelta(days=1),
        status="scheduled",
        source="test",
    )
    db_session.add(match)
    await db_session.flush()

    prediction = Prediction(
        match_id=match.id,
        user_id=user.id,
        home_prob=0.55,
        draw_prob=0.2,
        away_prob=0.25,
        status="READY",
        source="test",
        timestamp=datetime.utcnow(),
    )
    db_session.add(prediction)
    await db_session.commit()

    mission = await get_mission_control(db=db_session, admin=user)
    assert mission["kpis"]["total_users"] >= 1
    assert mission["kpis"]["predictions_today"] >= 1

    revenue = await platform_revenue(db=db_session, admin=user)
    assert "by_currency" in revenue
    assert "revenue_30d" in revenue


@pytest.mark.asyncio
async def test_admin_api_key_usage_stats_aggregates_usage_logs(db_session):
    user = User(email="api-admin@example.com", username="api_admin", hashed_password="hash", role="admin")
    db_session.add(user)
    await db_session.flush()

    api_key = APIKey(user_id=user.id, name="demo-key", key_prefix="vit_1234", key_hash="hash", plan="pro")
    db_session.add(api_key)
    await db_session.flush()

    log = APIUsageLog(
        api_key_id=api_key.id,
        user_id=user.id,
        endpoint="/api/testing",
        method="GET",
        status_code=503,
        latency_ms=125,
        called_at=datetime.utcnow(),
    )
    db_session.add(log)
    await db_session.commit()

    result = await api_key_usage_stats(days=7, db=db_session, admin=user)

    assert result["days"] == 7
    assert result["top_consumers"][0]["key_id"] == api_key.id
    assert result["top_consumers"][0]["errors_5xx"] == 1


@pytest.mark.asyncio
async def test_finance_admin_metrics_use_chain_and_wallet_ledger(db_session, monkeypatch):
    user = User(email="finance-admin@example.com", username="finance_admin", hashed_password="hash", role="super_admin")
    db_session.add(user)
    await db_session.flush()

    wallet = Wallet(
        id="wallet-finance",
        user_id=user.id,
        usd_balance=Decimal("120.50"),
        usdt_balance=Decimal("79.50"),
        vitcoin_balance=Decimal("25"),
        staked_vitcoin_balance=Decimal("5"),
    )
    db_session.add(wallet)
    db_session.add(WalletTransaction(
        id="tx-finance-fee",
        user_id=user.id,
        wallet_id=wallet.id,
        type="fee",
        currency="USD",
        amount=Decimal("12.75"),
        direction="credit",
        status="confirmed",
        reference="ref-finance-fee",
    ))
    db_session.add(MatchSettlement(
        id="settlement-finance",
        match_id="finance-match",
        consensus_id="finance-consensus",
        oracle_result="home",
        burn_amount=Decimal("3.25"),
        settled_at=datetime.now().replace(tzinfo=None),
    ))
    await db_session.commit()

    class FakeChainClient:
        async def status(self):
            return {"block_height": 4321, "connected_peers": 4}

        async def metrics(self):
            return {"tps": 8.5, "total_transactions": 900, "active_validators": 3}

        async def supply(self):
            return {
                "total_supply": 1000,
                "circulating_supply": 800,
                "burned_supply": 20,
                "staked_supply": 200,
            }

    monkeypatch.setattr(admin_finance, "VitChainClient", FakeChainClient)

    vitals = await admin_finance.get_blockchain_vitals(db=db_session, admin=user)
    treasury = await admin_finance.get_treasury_summary(db=db_session, admin=user)

    assert vitals["block_height"] == 4321
    assert vitals["tps"] == 8.5
    assert vitals["mempool_size"] is None
    assert treasury["total_reserves_usd"] == 200
    assert treasury["circulating_supply"] == 800
    assert treasury["burned_tokens"] == 20
    assert treasury["monthly_revenue_by_currency"]["USD"] == 12.75
    assert treasury["staked_ratio"] == "20.00%"
    assert treasury["burn_rate_24h"] == 3.25


@pytest.mark.asyncio
async def test_public_blockchain_metrics_use_authoritative_chain_values(monkeypatch):
    class FakeChainClient:
        async def status(self):
            return {"block_height": 4321}

        async def metrics(self):
            return {"tps": 8.5, "total_transactions": 900, "active_validators": 3}

        async def supply(self):
            return {
                "total_supply": "1000",
                "circulating_supply": "800",
                "burned_supply": "20",
                "staked_supply": "200",
            }

    monkeypatch.setattr(blockchain_routes, "resolve_chain_mode", lambda: "external")
    monkeypatch.setattr(blockchain_routes, "VitChainClient", FakeChainClient)

    result = await blockchain_routes.network_blockchain_metrics(db=None)

    assert result["source"] == "vit-chain"
    assert result["block_height"] == 4321
    assert result["total_transactions"] == 900
    assert result["circulating_supply"] == 800
    assert result["tps"] == 8.5
    assert result["block_time"] is None
    assert result["finality"] is None
