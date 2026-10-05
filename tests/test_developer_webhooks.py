import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.modules.developer.models import APIKey, WebhookEndpoint, WebhookDeliveryLog
from app.auth.jwt_utils import create_access_token


@pytest.fixture
async def dev_user(db_session: AsyncSession):
    user = User(
        email="dev_webhooks_user@vit.network",
        username="dev_webhooks_user",
        hashed_password="hashed_pass_test",
        is_active=True,
        role="user",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def user_headers(dev_user: User):
    token = create_access_token({"sub": str(dev_user.id), "email": dev_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_key_rotation_and_update(client: AsyncClient, user_headers: dict):
    # 1. Create key
    res = await client.post("/api/developer/keys", json={"name": "Original Key Name", "plan": "free"}, headers=user_headers)
    assert res.status_code == 201
    key_id = res.json()["id"]
    old_prefix = res.json()["key_prefix"]

    # 2. Update key
    update_res = await client.patch(f"/api/developer/keys/{key_id}", json={"name": "Updated Key Name", "plan": "starter"}, headers=user_headers)
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Key Name"
    assert update_res.json()["plan"] == "starter"

    # 3. Rotate / regenerate key
    regen_res = await client.post(f"/api/developer/keys/{key_id}/regenerate", headers=user_headers)
    assert regen_res.status_code == 200
    new_data = regen_res.json()
    assert new_data["key_prefix"] != old_prefix
    assert new_data["key"].startswith("vit_")


@pytest.mark.asyncio
async def test_webhook_crud_and_testing(client: AsyncClient, user_headers: dict, db_session: AsyncSession):
    # 1. Create webhook
    create_res = await client.post(
        "/api/developer/webhooks",
        json={
            "url": "https://httpbin.org/post",
            "description": "Test Webhook Endpoint",
            "events": ["prediction.resolved", "match.started"]
        },
        headers=user_headers,
    )
    assert create_res.status_code == 201
    data = create_res.json()
    assert data["url"] == "https://httpbin.org/post"
    assert data["secret"].startswith("whsec_")
    webhook_id = data["id"]

    # 2. List webhooks
    list_res = await client.get("/api/developer/webhooks", headers=user_headers)
    assert list_res.status_code == 200
    webhooks = list_res.json()
    assert len(webhooks) >= 1
    assert any(w["id"] == webhook_id for w in webhooks)

    # 3. Update webhook
    patch_res = await client.patch(
        f"/api/developer/webhooks/{webhook_id}",
        json={"is_active": False, "description": "Disabled webhook"},
        headers=user_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_active"] is False

    # 4. Trigger test ping
    test_res = await client.post(
        f"/api/developer/webhooks/{webhook_id}/test",
        json={"event_type": "ping", "payload": {"test": True}},
        headers=user_headers,
    )
    assert test_res.status_code == 200
    test_data = test_res.json()
    assert test_data["webhook_id"] == webhook_id
    assert "log" in test_data

    # 5. Fetch delivery logs
    logs_res = await client.get(f"/api/developer/webhooks/{webhook_id}/logs", headers=user_headers)
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 1
    assert logs[0]["event_type"] == "ping"

    # 6. Delete webhook
    del_res = await client.delete(f"/api/developer/webhooks/{webhook_id}", headers=user_headers)
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True
