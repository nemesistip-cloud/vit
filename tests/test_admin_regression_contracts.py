from decimal import Decimal

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from app.api.dependencies.admin import require_admin
from app.api.deps import get_current_admin
from app.db.models import User
from app.modules.kyc.models import KYCSubmission, KYCStatus
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
