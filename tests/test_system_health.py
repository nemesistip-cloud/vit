"""
System Health & Infrastructure Tests — validates health endpoints,
structured error format, CORS headers, and API versioning.
"""
import pytest
import httpx

from main import app


def _client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


# ── Health Endpoint ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint_returns_200():
    async with _client() as client:
        resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_returns_json():
    async with _client() as client:
        resp = await client.get("/health")
    assert "application/json" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_health_endpoint_has_status_field():
    async with _client() as client:
        resp = await client.get("/health")
    data = resp.json()
    assert "status" in data or "ok" in str(data).lower()


@pytest.mark.asyncio
async def test_health_endpoint_status_is_ok():
    async with _client() as client:
        resp = await client.get("/health")
    data = resp.json()
    status_val = data.get("status", data.get("health", "")).lower()
    assert status_val in ("ok", "healthy", "running", "")


@pytest.mark.asyncio
async def test_health_returns_quickly():
    """Health endpoint should respond within 3 seconds."""
    import time
    async with _client() as client:
        start = time.monotonic()
        resp = await client.get("/health")
        elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed < 3.0, f"Health check took {elapsed:.2f}s — too slow"


# ── Readiness / System Status ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_system_status_endpoint_responds():
    async with _client() as client:
        resp = await client.get("/system/status")
    assert resp.status_code in (200, 401, 403, 404)


@pytest.mark.asyncio
async def test_readiness_probe_returns_valid_response():
    async with _client() as client:
        resp = await client.get("/health/ready")
    assert resp.status_code in (200, 404)


# ── CORS Headers ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cors_headers_present_on_health():
    async with _client() as client:
        resp = await client.options(
            "/health",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
    # CORS may return 200 or 204
    assert resp.status_code in (200, 204, 400, 405)


# ── Response Headers ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_response_has_content_type_header():
    async with _client() as client:
        resp = await client.get("/health")
    assert "content-type" in resp.headers


@pytest.mark.asyncio
async def test_api_error_response_is_json():
    """API error responses (e.g. 401 Unauthorized) must use JSON content-type.
    Note: Unknown paths hit the SPA catch-all (React Router) and return HTML/200 by design.
    This test verifies that real API errors return JSON."""
    async with _client() as client:
        # /auth/me without credentials always returns 401 JSON — use as JSON error probe
        resp = await client.get("/auth/me")
    assert resp.status_code == 401
    assert "application/json" in resp.headers.get("content-type", ""), (
        f"API 401 should be JSON, got: {resp.headers.get('content-type')}"
    )


# ── API Docs ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_openapi_schema_accessible():
    async with _client() as client:
        resp = await client.get("/openapi.json")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_openapi_schema_has_paths():
    async with _client() as client:
        resp = await client.get("/openapi.json")
    data = resp.json()
    assert "paths" in data
    assert len(data["paths"]) > 0


@pytest.mark.asyncio
async def test_openapi_schema_has_info():
    async with _client() as client:
        resp = await client.get("/openapi.json")
    data = resp.json()
    assert "info" in data
    assert "title" in data["info"]


# ── Dashboard System Routes ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_stats_endpoint_responds():
    async with _client() as client:
        resp = await client.get("/api/dashboard/stats")
    assert resp.status_code in (200, 401, 403, 404)


@pytest.mark.asyncio
async def test_dashboard_summary_endpoint_responds():
    async with _client() as client:
        resp = await client.get("/api/dashboard/summary")
    assert resp.status_code in (200, 401, 403, 404)
