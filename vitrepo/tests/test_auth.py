"""
Tests for authentication endpoints: register, login, /auth/me, refresh.
"""
import uuid
import pytest
import httpx

from main import app


def _client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


def _unique_email():
    return f"auth_test_{uuid.uuid4().hex[:8]}@vit.network"


@pytest.mark.asyncio
async def test_register_creates_user_and_returns_tokens():
    async with _client() as client:
        resp = await client.post("/auth/register", json={
            "email": _unique_email(),
            "username": f"user_{uuid.uuid4().hex[:6]}",
            "password": "Secure123!",
        })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "user_id" in data
    assert "role" in data


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409():
    email = _unique_email()
    payload = {"email": email, "username": f"u_{uuid.uuid4().hex[:6]}", "password": "Secure123!"}
    async with _client() as client:
        await client.post("/auth/register", json=payload)
        resp = await client.post("/auth/register", json={**payload, "username": f"u_{uuid.uuid4().hex[:6]}"})
    assert resp.status_code in (409, 400)


@pytest.mark.asyncio
async def test_register_weak_password_returns_error():
    async with _client() as client:
        resp = await client.post("/auth/register", json={
            "email": _unique_email(),
            "username": "weakpassuser",
            "password": "123",
        })
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_login_returns_tokens():
    email = _unique_email()
    username = f"login_{uuid.uuid4().hex[:6]}"
    password = "LoginPass1!"
    async with _client() as client:
        await client.post("/auth/register", json={"email": email, "username": username, "password": password})
        resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401():
    email = _unique_email()
    async with _client() as client:
        await client.post("/auth/register", json={
            "email": email, "username": f"u_{uuid.uuid4().hex[:6]}", "password": "Correct123!"
        })
        resp = await client.post("/auth/login", json={"email": email, "password": "WrongPass!"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_valid_token():
    email = _unique_email()
    username = f"me_{uuid.uuid4().hex[:6]}"
    async with _client() as client:
        reg = await client.post("/auth/register", json={
            "email": email, "username": username, "password": "MeTest123!"
        })
        token = reg.json()["access_token"]
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == email


@pytest.mark.asyncio
async def test_get_me_without_token_returns_401():
    async with _client() as client:
        resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_returns_new_access_token():
    email = _unique_email()
    async with _client() as client:
        reg = await client.post("/auth/register", json={
            "email": email, "username": f"ref_{uuid.uuid4().hex[:6]}", "password": "Refresh123!"
        })
        refresh_token = reg.json()["refresh_token"]
        resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401():
    async with _client() as client:
        resp = await client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401
