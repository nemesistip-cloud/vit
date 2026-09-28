from decimal import Decimal
from types import SimpleNamespace

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from app.api.dependencies.admin import require_admin, require_super_admin
from app.api.deps import get_current_admin
from app.db.models import User
from app.api.routes.dashboard import get_model_confidence
from app.modules.ai.models import ModelMetadata
from app.modules.ai.registry import bootstrap_registry
from app.modules.blockchain.models import ValidatorProfile, ValidatorStatus
from app.modules.kyc.models import KYCSubmission, KYCStatus
from app.modules.notifications.service import NotificationService
from app.modules.wallet.models import Wallet, WalletTransaction


@pytest.mark.asyncio
async def test_admin_wallet_transactions_uses_real_schema(client, db_session):
    admin = User(email="admin.wallet@example.com", username="admin_wallet", role="admin", is_active=True)
    db_session.add(admin)
    await db_session.flush()

    wallet = Wallet(user_id=admin.id)
    db_session.add(wallet)
    await db_session.flush()

    tx = WalletTransaction(
        user_id=admin.id,
        wallet_id=wallet.id,
        type="deposit",
        currency="VITCoin",
        amount=Decimal("12.50"),
        direction="credit",
        status="confirmed",
        description="Admin wallet regression check",
        reference="admin-wallet-regression-1",
    )
    db_session.add(tx)
    await db_session.commit()

    app.dependency_overrides[require_admin] = lambda: admin
    try:
        resp = await client.get("/api/admin/wallet/transactions?limit=30")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1
        assert any(item["user_id"] == admin.id for item in data["transactions"])
    finally:
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_admin_kyc_queue_accepts_all_status_filter(client, db_session):
    admin = User(email="admin.kyc@example.com", username="admin_kyc", role="admin", is_active=True)
    db_session.add(admin)
    await db_session.flush()

    submission = KYCSubmission(
        user_id=admin.id,
        full_name="KYC Admin User",
        date_of_birth="1989-03-10",
        nationality="Nigerian",
        document_type="national_id",
        document_number="ABC123",
        status=KYCStatus.PENDING,
        risk_score=5,
    )
    db_session.add(submission)
    await db_session.commit()

    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        resp = await client.get("/api/kyc/admin/queue?status=all&limit=10")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["count"] >= 1
        assert any(item["user_id"] == admin.id for item in data["items"])
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


@pytest.mark.asyncio
async def test_admin_kyc_compatibility_alias_lists_pending_requests(client, db_session):
    admin = User(email="admin.kyc.alias@example.com", username="admin_kyc_alias", role="admin", is_active=True)
    db_session.add(admin)
    await db_session.commit()

    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        response = await client.get("/api/admin/kyc")
        assert response.status_code == 200, response.text
        assert response.json() == {"total": 0, "kyc_requests": []}
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


@pytest.mark.asyncio
async def test_validator_approval_preserves_super_admin_role(client, db_session, monkeypatch):
    admin = User(email="admin.validator@example.com", username="admin_validator", role="super_admin", is_active=True)
    db_session.add(admin)
    await db_session.flush()

    validator = ValidatorProfile(
        user_id=admin.id,
        stake_amount=Decimal("5"),
        trust_score=Decimal("0.5"),
        influence_score=Decimal("2.5"),
        status=ValidatorStatus.PENDING.value,
    )
    db_session.add(validator)
    await db_session.commit()

    async def no_notification(*args, **kwargs):
        return None

    monkeypatch.setattr(NotificationService, "notify_validator_status", no_notification)
    app.dependency_overrides[require_super_admin] = lambda: admin
    try:
        response = await client.post(f"/api/blockchain/admin/validators/{validator.id}/approve")
        assert response.status_code == 200, response.text
        assert response.json()["validator"]["status"] == ValidatorStatus.ACTIVE.value
        assert response.json()["validator"]["role"] == "super_admin"
    finally:
        app.dependency_overrides.pop(require_super_admin, None)


@pytest.mark.asyncio
async def test_model_confidence_does_not_invent_accuracy_for_unmeasured_models(db_session):
    db_session.add_all([
        ModelMetadata(key="measured", name="Measured", model_type="test", accuracy=0.63, weight=2, is_active=True),
        ModelMetadata(key="unmeasured", name="Unmeasured", model_type="test", accuracy=None, weight=1, is_active=True),
        ModelMetadata(key="inactive", name="Inactive", model_type="test", accuracy=0.99, weight=5, is_active=False),
    ])
    await db_session.commit()

    result = await get_model_confidence(db_session)
    models = {model["key"]: model for model in result["models"]}

    assert models["measured"]["accuracy"] == 63.0
    assert models["unmeasured"]["accuracy"] is None
    assert result["active_count"] == 2
    assert result["measured_count"] == 1
    assert result["ensemble_accuracy"] == 63.0


@pytest.mark.asyncio
async def test_model_confidence_reports_no_accuracy_for_empty_registry(db_session):
    result = await get_model_confidence(db_session)

    assert result["models"] == []
    assert result["active_count"] == 0
    assert result["measured_count"] == 0
    assert result["ensemble_accuracy"] is None


@pytest.mark.asyncio
async def test_model_registry_bootstrap_preserves_missing_accuracy(db_session):
    model = ModelMetadata(
        key="xgb_v2",
        name="XGBoost",
        model_type="XGBoost",
        accuracy=None,
        weight=0.12,
        is_active=True,
    )
    db_session.add(model)
    await db_session.commit()

    await bootstrap_registry(db_session, SimpleNamespace(model_meta={}))
    await db_session.refresh(model)

    assert model.accuracy is None
