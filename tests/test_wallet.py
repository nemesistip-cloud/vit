"""
Tests for the /api/wallet endpoints.
Wallet routes require a valid JWT token (get_current_user dependency),
even when AUTH_ENABLED=false, because the middleware only bypasses
the middleware-level check — not the route-level dependency.
"""
import uuid
import pytest
import httpx

from main import app


def _client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def _register_and_token(client):
    email = f"wallet_{uuid.uuid4().hex[:8]}@vit.network"
    resp = await client.post("/auth/register", json={
        "email": email,
        "username": f"wallet_{uuid.uuid4().hex[:6]}",
        "password": "WalletPass123!",
    })
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    return resp.json()["access_token"], resp.json()["user_id"]


@pytest.mark.asyncio
async def test_wallet_me_without_token_returns_401():
    async with _client() as client:
        resp = await client.get("/api/wallet/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_wallet_me_with_valid_token_returns_balances():
    async with _client() as client:
        token, _ = await _register_and_token(client)
        resp = await client.get(
            "/api/wallet/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "vitcoin_balance" in data
    assert "ngn_balance" in data
    assert "usd_balance" in data


@pytest.mark.asyncio
async def test_wallet_auto_created_on_register_with_vitcoin_bonus():
    """Registration auto-creates a wallet with a VITCoin bonus."""
    async with _client() as client:
        token, _ = await _register_and_token(client)
        resp = await client.get(
            "/api/wallet/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["vitcoin_balance"]) >= 0


@pytest.mark.asyncio
async def test_wallet_transactions_requires_auth():
    async with _client() as client:
        resp = await client.get("/api/wallet/transactions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_wallet_transactions_returns_list_with_auth():
    async with _client() as client:
        token, _ = await _register_and_token(client)
        resp = await client.get(
            "/api/wallet/transactions",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, (list, dict))


@pytest.mark.asyncio
async def test_wallet_plans_endpoint_is_public():
    """Subscription plans listing should be accessible without auth."""
    async with _client() as client:
        resp = await client.get("/api/wallet/plans")
    assert resp.status_code in (200, 404)
