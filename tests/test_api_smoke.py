import httpx
import pytest
from starlette.testclient import TestClient

from main import app
from app.modules.notifications.service import NotificationService


@pytest.mark.asyncio
async def test_health_returns_correlation_headers():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health", headers={"X-Request-ID": "pytest-health"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "pytest-health"
    assert response.headers["X-Correlation-ID"] == "pytest-health"
    assert response.json()["db_connected"] is True


@pytest.mark.asyncio
async def test_validation_error_uses_structured_envelope():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/auth/login", json={}, headers={"X-Request-ID": "pytest-validation"})

    payload = response.json()
    assert response.status_code == 422
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["request_id"] == "pytest-validation"
    assert response.headers["X-Request-ID"] == "pytest-validation"


def test_notifications_websocket_connects_and_pongs(monkeypatch):
    async def fake_unread_count(db, user_id):
        return 0

    async def fake_mark_read(db, user_id, notification_id):
        return True

    monkeypatch.setattr(NotificationService, "unread_count", fake_unread_count)
    monkeypatch.setattr(NotificationService, "mark_read", fake_mark_read)

    from app.auth.jwt_utils import create_access_token
    token = create_access_token({"sub": "1", "role": "user"})

    # Ensure actual notification routes are eagerly mounted for the test client
    from app.modules.notifications.websocket import router as notifications_ws_router
    if not any(getattr(route, "path", None) == "/api/notifications/ws/{user_id}" for route in app.routes):
        app.include_router(notifications_ws_router)

    client = TestClient(app)
    with client.websocket_connect(f"/api/notifications/ws/1?token={token}") as websocket:
        assert websocket.receive_json() == {"action": "connected", "unread_count": 0}
        websocket.send_json({"action": "ping"})
        assert websocket.receive_json() == {"action": "pong"}


@pytest.mark.asyncio
async def test_compatibility_aliases_exist_for_frontend_routes():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        health = await client.get("/api/health")
        assert health.status_code == 200

        unauth_kys = await client.post("/api/kyc/submit", json={"full_name": "Test User"})
        assert unauth_kys.status_code in {401, 422}

        auth_resp = await client.post(
            "/api/auth/login",
            json={"email": "admin@vit.network", "password": "admin123"},
        )
        assert auth_resp.status_code in {200, 401}

        if auth_resp.status_code == 200:
            token = auth_resp.json().get("access_token")
            if token:
                admin_overview = await client.get(
                    "/api/admin/overview",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert admin_overview.status_code == 200

                admin_appeals = await client.get(
                    "/api/admin/appeals",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert admin_appeals.status_code == 200


@pytest.mark.asyncio
async def test_leaderboard_and_governance_route_validation():
    from app.auth.jwt_utils import create_access_token
    token = create_access_token({"sub": "1", "role": "user"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Leaderboard public endpoint
        res = await client.get("/api/leaderboard")
        assert res.status_code in {200, 503}  # 200 if DB available, 503 if DB unavail

        # Valid category param
        res_winrate = await client.get("/api/leaderboard?category=win_rate")
        assert res_winrate.status_code in {200, 503}

        # Invalid category param should trigger validation error (422)
        res_invalid = await client.get("/api/leaderboard?category=invalid_cat")
        assert res_invalid.status_code == 422

        # 2. Governance proposals endpoint (unauthenticated)
        gov_unauth = await client.get("/api/governance/proposals")
        assert gov_unauth.status_code in {401, 403}

        # Governance proposals with invalid status param and token
        gov_invalid = await client.get("/api/governance/proposals?status=invalid_status", headers=headers)
        assert gov_invalid.status_code in {400, 401, 422, 503}
