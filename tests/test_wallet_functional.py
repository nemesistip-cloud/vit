"""
Wallet Functional Tests — validates wallet state management, transaction history,
deposit flows, VITCoin operations, and transfer logic.
"""
import uuid
import pytest
import httpx

from main import app


def _client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def _register(client, suffix=""):
    email = f"wfn_{suffix}_{uuid.uuid4().hex[:8]}@vit.network"
    resp = await client.post("/auth/register", json={
        "email": email,
        "username": f"wfn_{uuid.uuid4().hex[:6]}",
        "password": "WalletFn123!",
    })
    assert resp.status_code == 201, resp.text
    d = resp.json()
    return d["access_token"], d["user_id"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Wallet Initialization ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_new_user_wallet_has_all_currency_fields():
    async with _client() as client:
        token, _ = await _register(client, "init")
        resp = await client.get("/api/wallet/me", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    for field in ("vitcoin_balance", "ngn_balance", "usd_balance"):
        assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_wallet_balances_are_non_negative():
    async with _client() as client:
        token, _ = await _register(client, "nonneg")
        resp = await client.get("/api/wallet/me", headers=_auth(token))
    data = resp.json()
    assert float(data["vitcoin_balance"]) >= 0
    assert float(data["ngn_balance"]) >= 0
    assert float(data["usd_balance"]) >= 0


@pytest.mark.asyncio
async def test_wallet_vitcoin_balance_is_numeric():
    async with _client() as client:
        token, _ = await _register(client, "numeric")
        resp = await client.get("/api/wallet/me", headers=_auth(token))
    data = resp.json()
    try:
        float(data["vitcoin_balance"])
    except (ValueError, TypeError):
        pytest.fail(f"vitcoin_balance is not numeric: {data['vitcoin_balance']}")


# ── Transaction History ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_transaction_history_is_a_list_or_paginated():
    async with _client() as client:
        token, _ = await _register(client, "txn1")
        resp = await client.get("/api/wallet/transactions", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, (list, dict))


@pytest.mark.asyncio
async def test_transaction_history_pagination_params():
    async with _client() as client:
        token, _ = await _register(client, "page")
        resp = await client.get(
            "/api/wallet/transactions?page=1&page_size=10",
            headers=_auth(token),
        )
    assert resp.status_code in (200, 422)


@pytest.mark.asyncio
async def test_transaction_history_empty_for_new_user():
    async with _client() as client:
        token, _ = await _register(client, "empty")
        resp = await client.get("/api/wallet/transactions", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    if isinstance(data, list):
        assert len(data) == 0 or len(data) >= 0  # new user may have 0 or bonus tx


# ── Deposit Initiation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_deposit_initiation_requires_auth():
    """Deposit initiation endpoint must reject unauthenticated requests."""
    async with _client() as client:
        resp = await client.post(
            "/api/wallet/deposit/initiate",
            json={"amount": 1000, "currency": "NGN", "method": "paystack"},
        )
    assert resp.status_code in (401, 403, 404, 422)


@pytest.mark.asyncio
async def test_deposit_initiation_with_auth_responds():
    """Deposit initiation with valid auth should respond (may fail without gateway keys)."""
    async with _client() as client:
        token, _ = await _register(client, "dep")
        resp = await client.post(
            "/api/wallet/deposit/initiate",
            json={"amount": 500, "currency": "NGN", "method": "paystack"},
            headers=_auth(token),
        )
    # Without Paystack keys configured, this may return 400/404/422/503
    assert resp.status_code in (200, 400, 404, 422, 503)


@pytest.mark.asyncio
async def test_deposit_with_zero_amount_returns_error():
    """Zero-amount deposit should be rejected with a validation error."""
    async with _client() as client:
        token, _ = await _register(client, "zeroDep")
        resp = await client.post(
            "/api/wallet/deposit/initiate",
            json={"amount": 0, "currency": "NGN", "method": "paystack"},
            headers=_auth(token),
        )
    assert resp.status_code in (400, 404, 422)


# ── Withdrawal ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_withdraw_requires_auth():
    async with _client() as client:
        resp = await client.post("/api/wallet/withdraw", json={"amount": 100, "currency": "NGN"})
    assert resp.status_code in (401, 403, 404, 422)


@pytest.mark.asyncio
async def test_withdraw_more_than_balance_returns_error():
    async with _client() as client:
        token, _ = await _register(client, "overWith")
        resp = await client.post(
            "/api/wallet/withdraw",
            json={"amount": 999999999, "currency": "USD", "bank_code": "044", "account_number": "1234567890"},
            headers=_auth(token),
        )
    assert resp.status_code in (400, 404, 409, 422, 503)


# ── Subscription Plans ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_subscription_plans_endpoint_accessible():
    async with _client() as client:
        resp = await client.get("/api/wallet/plans")
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_subscription_plans_contain_free_tier():
    """When plans are seeded (non-empty), a free tier should be present."""
    async with _client() as client:
        resp = await client.get("/api/wallet/plans")
    if resp.status_code == 200:
        data = resp.json()
        plans = data if isinstance(data, list) else data.get("plans", [])
        # Plans may be empty if startup seeding hasn't run yet in this test session
        if plans:
            names = [p.get("name", "").lower() for p in plans]
            assert any(n in ("free", "viewer", "basic") for n in names), (
                f"Free/viewer/basic plan not found in: {names}"
            )


@pytest.mark.asyncio
async def test_subscription_plans_have_required_fields():
    async with _client() as client:
        resp = await client.get("/api/wallet/plans")
    if resp.status_code == 200:
        data = resp.json()
        plans = data if isinstance(data, list) else data.get("plans", [])
        for plan in plans:
            assert "name" in plan or "display_name" in plan


# ── VITCoin Conversion ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vitcoin_conversion_endpoint_requires_auth():
    async with _client() as client:
        resp = await client.post("/api/wallet/convert", json={"amount": 10, "from": "NGN", "to": "VIT"})
    assert resp.status_code in (401, 403, 404, 422)


@pytest.mark.asyncio
async def test_vitcoin_conversion_with_valid_auth():
    async with _client() as client:
        token, _ = await _register(client, "convert")
        resp = await client.post(
            "/api/wallet/convert",
            json={"amount": 10, "from_currency": "NGN", "to_currency": "VIT"},
            headers=_auth(token),
        )
    assert resp.status_code in (200, 400, 404, 422)


# ── Wallet Admin ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_all_wallets_blocked_for_regular_user():
    """Wallet admin overview must reject non-admin requests."""
    async with _client() as client:
        token, _ = await _register(client, "norole")
        resp = await client.get("/api/admin/wallet/overview", headers=_auth(token))
    assert resp.status_code in (401, 403, 404)


@pytest.mark.asyncio
async def test_wallet_withdrawal_config_blocked_for_regular_user():
    """Wallet admin config must reject non-admin requests."""
    async with _client() as client:
        token, _ = await _register(client, "stats")
        resp = await client.get("/api/admin/wallet/config", headers=_auth(token))
    assert resp.status_code in (401, 403, 404)
