import os
import sys
import uuid
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("VIT_DATABASE_URL", "sqlite+aiosqlite:///./vit.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-for-pytest-only")
os.environ.setdefault("SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FOOTBALL_DATA_API_KEY", "")
os.environ.setdefault("THE_ODDS_API_KEY", "")
os.environ.setdefault("ODDS_API_KEY", "")
os.environ.setdefault("USE_REAL_ML_MODELS", "false")
os.environ.setdefault("BLOCKCHAIN_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")


@pytest.fixture
def base_url():
    return "http://testserver"


@pytest.fixture
async def client(base_url):
    from main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=base_url) as ac:
        yield ac


@pytest.fixture
def unique_email():
    return f"test_{uuid.uuid4().hex[:8]}@vit.network"


@pytest.fixture
async def registered_user(client, unique_email):
    """Register a fresh user and return their credentials + token response."""
    payload = {
        "email": unique_email,
        "username": f"tester_{uuid.uuid4().hex[:6]}",
        "password": "TestPass123!",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201, f"Registration failed: {response.text}"
    data = response.json()
    return {
        "email": unique_email,
        "password": payload["password"],
        "username": payload["username"],
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user_id": data["user_id"],
        "role": data["role"],
    }


@pytest.fixture
def auth_headers(registered_user):
    """Bearer auth headers built from a freshly registered user."""
    return {"Authorization": f"Bearer {registered_user['access_token']}"}