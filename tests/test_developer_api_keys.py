import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.modules.developer.models import APIKey
from app.auth.jwt_utils import create_access_token


@pytest.fixture
async def test_admin_user(db_session: AsyncSession):
    user = User(
        email="admin_dev_test@vit.network",
        username="admin_dev_test",
        hashed_password="hashed_pass_test",
        is_active=True,
        role="admin",
        admin_role="super_admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_normal_user(db_session: AsyncSession):
    user = User(
        email="user_dev_test@vit.network",
        username="user_dev_test",
        hashed_password="hashed_pass_test",
        is_active=True,
        role="user",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(test_admin_user: User):
    token = create_access_token({"sub": str(test_admin_user.id), "email": test_admin_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers(test_normal_user: User):
    token = create_access_token({"sub": str(test_normal_user.id), "email": test_normal_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_developer_api_key_admin(client: AsyncClient, admin_headers: dict, test_admin_user: User, db_session: AsyncSession):
    # Call alias endpoint /api/developer/api-keys
    res = await client.post(
        "/api/developer/api-keys",
        json={"name": "Admin Test Key"},
        headers=admin_headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Admin Test Key"
    assert "key" in data and data["key"].startswith("vit_")
    assert "raw_value" in data and data["raw_value"] == data["key"]
    assert data["key_prefix"] == data["key"][:12]

    # Verify database persistence & secret hashing
    key_id = data["id"]
    db_key = await db_session.get(APIKey, key_id)
    assert db_key is not None
    assert db_key.user_id == test_admin_user.id
    assert db_key.key_plain is None
    assert db_key.key_hash is not None


@pytest.mark.asyncio
async def test_create_developer_api_key_user(client: AsyncClient, user_headers: dict, test_normal_user: User):
    # Call canonical endpoint /api/developer/keys
    res = await client.post(
        "/api/developer/keys",
        json={"name": "User Standard Key"},
        headers=user_headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "User Standard Key"
    assert data["plan"] == "free"


@pytest.mark.asyncio
async def test_unauthenticated_api_key_creation(client: AsyncClient):
    res = await client.post("/api/developer/api-keys", json={"name": "No Auth Key"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_api_key_listing_does_not_expose_secrets(client: AsyncClient, admin_headers: dict):
    # Create key first
    await client.post("/api/developer/api-keys", json={"name": "Key For List"}, headers=admin_headers)

    # List keys via /api/developer/api-keys
    res = await client.get("/api/developer/api-keys", headers=admin_headers)
    assert res.status_code == 200
    keys = res.json()
    assert len(keys) >= 1
    first_key = keys[0]
    assert first_key["key"] is None


@pytest.mark.asyncio
async def test_api_key_revocation_and_deletion(client: AsyncClient, admin_headers: dict, db_session: AsyncSession):
    # Create key
    res = await client.post("/api/developer/api-keys", json={"name": "Key to Revoke"}, headers=admin_headers)
    key_id = res.json()["id"]

    # Revoke key
    revoke_res = await client.patch(f"/api/developer/api-keys/{key_id}/revoke", headers=admin_headers)
    assert revoke_res.status_code == 200
    assert revoke_res.json()["revoked"] is True

    # Check DB state
    db_key = await db_session.get(APIKey, key_id)
    assert db_key.is_active is False
