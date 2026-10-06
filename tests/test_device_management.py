import pytest
from httpx import AsyncClient, ASGITransport
from app.services.device_service import parse_user_agent
from main import app


def test_parse_user_agent():
    """Test parsing platform and browser from various User-Agent strings."""
    mac_chrome = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    p, b = parse_user_agent(mac_chrome)
    assert p == "macOS"
    assert b == "Chrome"

    win_edge = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
    p, b = parse_user_agent(win_edge)
    assert p == "Windows"
    assert b == "Microsoft Edge"

    iphone_safari = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1"
    p, b = parse_user_agent(iphone_safari)
    assert p == "iOS"
    assert b == "Safari"

    android_ff = "Mozilla/5.0 (Android 14; Mobile; rv:123.0) Gecko/123.0 Firefox/123.0"
    p, b = parse_user_agent(android_ff)
    assert p == "Android"
    assert b == "Firefox"


@pytest.mark.asyncio
async def test_device_auto_registration_on_login_and_listing():
    """Test device registration upon login and fetching registered devices & sessions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"device_test_{import_time_nonce()}@example.com"
        password = "Password123!"

        reg_resp = await client.post(
            "/api/auth/register",
            json={"email": email, "username": f"devuser_{import_time_nonce()}", "password": password},
        )
        assert reg_resp.status_code in (200, 201)
        data = reg_resp.json()
        token = data["access_token"]

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            "X-Device-Id": "test_mac_device_001",
        }

        login_resp = await client.post(
            "/api/auth/login",
            json={"email": email, "password": password, "device_id": "test_mac_device_001"},
            headers=headers,
        )
        assert login_resp.status_code == 200

        # Check devices endpoint
        devices_resp = await client.get("/api/identity/me/devices", headers=headers)
        assert devices_resp.status_code == 200
        devices = devices_resp.json()
        assert len(devices) >= 1
        dev = next((d for d in devices if d["device_id"] == "test_mac_device_001"), None)
        assert dev is not None
        assert dev["platform"] == "macOS"
        assert dev["browser"] == "Chrome"
        assert dev["is_trusted"] is False

        # Check sessions endpoint
        sessions_resp = await client.get("/api/identity/me/sessions", headers=headers)
        assert sessions_resp.status_code == 200
        sessions = sessions_resp.json()
        assert len(sessions) >= 1
        assert sessions[0]["is_active"] is True

        # Trust device
        trust_resp = await client.post(
            f"/api/identity/me/devices/{dev['device_id']}/trust",
            headers=headers,
        )
        assert trust_resp.status_code == 200

        devices_resp2 = await client.get("/api/identity/me/devices", headers=headers)
        dev2 = next((d for d in devices_resp2.json() if d["device_id"] == "test_mac_device_001"), None)
        assert dev2 is not None
        assert dev2["is_trusted"] is True

        del_resp = await client.delete(
            f"/api/identity/me/devices/{dev['device_id']}",
            headers=headers,
        )
        assert del_resp.status_code in (200, 204)


def import_time_nonce() -> str:
    import time
    return str(int(time.time() * 1000))
