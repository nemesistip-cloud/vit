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


@pytest.mark.asyncio
async def test_developer_application_registration_is_authenticated_and_owner_scoped(
    client: AsyncClient, user_headers: dict, test_normal_user: User
):
    payload = {
        "slug": "sample-intelligence-app",
        "name": "Sample Intelligence App",
        "description": "An independently registered VIT ecosystem application.",
        "requested_scopes": ["identity.read", "prediction.read"],
    }
    unauthenticated = await client.post("/api/developer/apps", json=payload)
    assert unauthenticated.status_code == 401

    created = await client.post("/api/developer/apps", json=payload, headers=user_headers)
    assert created.status_code == 201
    assert created.json()["id"] == "app:sample-intelligence-app"
    assert created.json()["status"] == "draft"
    assert created.json()["requested_scopes"] == payload["requested_scopes"]

    listed = await client.get("/api/developer/apps", headers=user_headers)
    assert listed.status_code == 200
    assert [app["id"] for app in listed.json()] == [created.json()["id"]]


@pytest.mark.asyncio
async def test_application_scopes_are_allowlisted_and_admin_controls_publication(
    client: AsyncClient, user_headers: dict, admin_headers: dict
):
    payload = {
        "slug": "reviewable-app",
        "name": "Reviewable App",
        "description": "An application that must pass review before discovery.",
        "prod_url": "https://apps.example.test/reviewable-app",
        "requested_scopes": ["identity.read", "root.access"],
    }
    invalid = await client.post("/api/developer/apps", json=payload, headers=user_headers)
    assert invalid.status_code == 422

    payload["requested_scopes"] = ["identity.read", "prediction.read"]
    created = await client.post("/api/developer/apps", json=payload, headers=user_headers)
    app_id = created.json()["id"]
    assert created.status_code == 201

    hidden = await client.get("/api/apps")
    assert all(item["id"] != app_id for item in hidden.json())

    submitted = await client.post(f"/api/developer/apps/{app_id}/submit", headers=user_headers)
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "review_pending"

    forbidden_queue = await client.get("/api/developer/apps/review-queue", headers=user_headers)
    assert forbidden_queue.status_code == 403

    queue = await client.get("/api/developer/apps/review-queue", headers=admin_headers)
    assert queue.status_code == 200
    assert any(item["id"] == app_id for item in queue.json())

    approved = await client.post(
        f"/api/developer/apps/{app_id}/review",
        json={"decision": "approved", "reviewer_notes": "Scope request reviewed."},
        headers=admin_headers,
    )
    assert approved.status_code == 200

    scoped_key = await client.post(
        f"/api/developer/apps/{app_id}/keys",
        json={"name": "Reviewable app key"},
        headers=user_headers,
    )
    assert scoped_key.status_code == 201
    assert scoped_key.json()["app_id"] == app_id
    assert scoped_key.json()["scopes"] == ["identity.read", "prediction.read"]

    published = await client.post(f"/api/developer/apps/{app_id}/publish", headers=admin_headers)
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    catalog = await client.get("/api/apps")
    assert catalog.status_code == 200
    assert any(item["id"] == app_id for item in catalog.json())


def test_vitpredict_api_key_policy_is_app_and_scope_limited():
    from app.api.middleware.auth import _authorize_vitpredict_key

    assert _authorize_vitpredict_key(
        "GET", "/api/apps/vitpredict/matches/upcoming", "app:vitpredict", ["sports.read"]
    ) is None
    assert _authorize_vitpredict_key(
        "GET", "/api/apps/vitpredict/analytics/overview", "app:vitpredict", ["prediction.read"]
    ) == "Application key is missing required scope: models.evaluate"
    assert _authorize_vitpredict_key(
        "GET", "/api/wallet/balance", "app:vitpredict", ["wallet.read"]
    ) == "Application API keys are restricted to their registered app"


@pytest.mark.asyncio
async def test_vitpredict_api_key_middleware_enforces_app_scopes(client, monkeypatch, test_normal_user: User):
    from app.api.middleware import auth

    monkeypatch.setenv("AUTH_ENABLED", "true")

    async def scoped_key(_key):
        return True, "ok", test_normal_user.id, "free", "app:vitpredict", ["models.evaluate"]

    async def wrong_scope_key(_key):
        return True, "ok", test_normal_user.id, "free", "app:vitpredict", ["prediction.read"]

    async def wrong_app_key(_key):
        return True, "ok", test_normal_user.id, "free", "app:other", ["models.evaluate"]

    monkeypatch.setattr(auth, "_auth_developer_api_key", wrong_scope_key)
    wrong_scope = await client.get(
        "/api/apps/vitpredict/analytics/overview", headers={"x-api-key": "vit_test"}
    )
    assert wrong_scope.status_code == 403

    monkeypatch.setattr(auth, "_auth_developer_api_key", wrong_app_key)
    wrong_app = await client.get(
        "/api/apps/vitpredict/analytics/overview", headers={"x-api-key": "vit_test"}
    )
    assert wrong_app.status_code == 403

    monkeypatch.setattr(auth, "_auth_developer_api_key", scoped_key)
    allowed = await client.get(
        "/api/apps/vitpredict/analytics/overview", headers={"x-api-key": "vit_test"}
    )
    assert allowed.status_code == 200
