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

    client = TestClient(app)
    with client.websocket_connect("/api/notifications/ws/1") as websocket:
        assert websocket.receive_json() == {"action": "connected", "unread_count": 0}
        websocket.send_json({"action": "ping"})
        assert websocket.receive_json() == {"action": "pong"}