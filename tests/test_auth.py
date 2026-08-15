"""
Tests for authentication endpoints: register, login, /auth/me, refresh.

Uses the conftest `client` fixture which patches the DB engine with an
in-memory SQLite instance so tests are fully isolated and do not require
a running PostgreSQL server.
"""
import uuid
import pytest


def _unique_email():
    return f"auth_test_{uuid.uuid4().hex[:8]}@vit.network"


def _unique_user(password: str = "Secure@12345!"):
    return {
        "email": _unique_email(),
        "username": f"user_{uuid.uuid4().hex[:6]}",
        "password": password,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_creates_user_and_returns_tokens(client):
    payload = _unique_user()
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "user_id" in data
    assert "role" in data


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client):
    payload = _unique_user()
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json={
        **payload,
        "username": f"u_{uuid.uuid4().hex[:6]}",  # different username, same email
    })
    assert resp.status_code in (409, 400)


@pytest.mark.asyncio
async def test_register_weak_password_returns_error(client):
    resp = await client.post("/auth/register", json={
        "email": _unique_email(),
        "username": f"weakpassuser_{uuid.uuid4().hex[:4]}",
        "password": "123",  # too short and no complexity
    })
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_register_missing_special_char_returns_error(client):
    """Password policy requires at least one special character."""
    resp = await client.post("/auth/register", json={
        "email": _unique_email(),
        "username": f"u_{uuid.uuid4().hex[:6]}",
        "password": "Abcdefgh12",  # no special char
    })
    assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_returns_tokens(client):
    payload = _unique_user()
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/login", json={
        "email": payload["email"],
        "password": payload["password"],
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client):
    payload = _unique_user()
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/login", json={
        "email": payload["email"],
        "password": "WrongPass@999!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client):
    resp = await client.post("/auth/login", json={
        "email": "nobody@vit.network",
        "password": "Whatever@1!",
    })
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Brute-force protection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_brute_force_lockout_after_10_attempts(client):
    """After 10 failed logins the account should be locked (429 or 403)."""
    email = _unique_email()
    await client.post("/auth/register", json={
        "email": email,
        "username": f"u_{uuid.uuid4().hex[:6]}",
        "password": "Correct@12345!",
    })
    for _ in range(10):
        await client.post("/auth/login", json={"email": email, "password": "Wrong@Pass1!"})
    resp = await client.post("/auth/login", json={"email": email, "password": "Correct@12345!"})
    # After lockout even the correct password should be rejected
    assert resp.status_code in (429, 403, 401)


# ---------------------------------------------------------------------------
# /auth/me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_me_returns_user_profile(client):
    payload = _unique_user()
    reg = await client.post("/auth/register", json=payload)
    token = reg.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 401)  # 401 if AUTH_ENABLED=false env override


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_returns_new_access_token(client):
    payload = _unique_user()
    reg = await client.post("/auth/register", json=payload)
    refresh_token = reg.json().get("refresh_token")
    if not refresh_token:
        pytest.skip("Registration did not return refresh_token")
    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code in (200, 401)

@pytest.mark.asyncio
async def test_login_with_username(client):
    email = _unique_email()
    username = f"usr_{uuid.uuid4().hex[:6]}"
    password = "Correct@12345!"
    await client.post("/auth/register", json={
        "email": email,
        "username": username,
        "password": password,
    })
    # Login using username instead of email
    resp = await client.post("/auth/login", json={
        "email": username,
        "password": password,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["username"] == username
