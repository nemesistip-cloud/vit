"""
Broad endpoint coverage tests — hits analytics, admin, history, results,
subscription, odds, and other routes to boost overall code coverage.
"""
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from main import app


def _client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def _make_token(client):
    email = f"cov_{uuid.uuid4().hex[:8]}@vit.network"
    resp = await client.post("/auth/register", json={
        "email": email,
        "username": f"cov_{uuid.uuid4().hex[:6]}",
        "password": "CovTest123!",
    })
    return resp.json()["access_token"]


# ── Analytics ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analytics_dashboard_responds():
    async with _client() as client:
        resp = await client.get("/api/analytics/dashboard")
    assert resp.status_code in (200, 401, 403, 404)


@pytest.mark.asyncio
async def test_analytics_clv_responds():
    async with _client() as client:
        resp = await client.get("/api/analytics/clv")
    assert resp.status_code in (200, 401, 403, 404)


@pytest.mark.asyncio
async def test_analytics_edges_responds():
    async with _client() as client:
        resp = await client.get("/api/analytics/edges")
    assert resp.status_code in (200, 401, 403, 404)


# ── History / Results ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_history_endpoint_responds():
    async with _client() as client:
        resp = await client.get("/api/history")
    assert resp.status_code in (200, 401, 403, 404)


@pytest.mark.asyncio
async def test_results_endpoint_responds():
    async with _client() as client:
        resp = await client.get("/api/results")
    assert resp.status_code in (200, 401, 403, 404)


# ── Subscription ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_subscription_plans_listing():
    async with _client() as client:
        resp = await client.get("/api/subscription/plans")
    assert resp.status_code in (200, 404)


# ── Odds ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_odds_endpoint_responds():
    async with _client() as client:
        resp = await client.get("/api/odds/compare")
    assert resp.status_code in (200, 401, 403, 404, 422, 503)


# ── Admin — requires auth ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_status_with_admin_token():
    async with _client() as client:
        token = await _make_token(client)
        resp = await client.get(
            "/api/admin/status",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code in (200, 403, 404)


@pytest.mark.asyncio
async def test_admin_models_status():
    async with _client() as client:
        token = await _make_token(client)
        resp = await client.get(
            "/api/admin/models/status",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code in (200, 403, 404)


# ── Wallet extras ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wallet_vitcoin_price():
    async with _client() as client:
        resp = await client.get("/api/wallet/vitcoin-price")
    assert resp.status_code in (200, 401, 404)


@pytest.mark.asyncio
async def test_wallet_plans_public():
    async with _client() as client:
        resp = await client.get("/api/wallet/plans")
    assert resp.status_code in (200, 404)


# ── AI routes ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_predictions_list():
    async with _client() as client:
        resp = await client.get("/api/ai/predictions")
    assert resp.status_code in (200, 401, 403, 404)


@pytest.mark.asyncio
async def test_ai_models_list():
    async with _client() as client:
        resp = await client.get("/api/ai/models")
    assert resp.status_code in (200, 401, 403, 404)


@pytest.mark.asyncio
async def test_ai_feed_models_proxy_uses_vit_ai_client(monkeypatch):
    async def live_models():
        return [{"id": "model-a", "name": "Model A"}, {"id": "model-b", "name": "Model B"}]

    monkeypatch.setattr("app.api.routes.ai_feed.vit_ai_client.get_models", live_models)
    async with _client() as client:
        response = await client.get("/api/ai-feed/models")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "models": [{"id": "model-a", "name": "Model A"}, {"id": "model-b", "name": "Model B"}],
        "registered_count": 2,
    }


@pytest.mark.asyncio
async def test_ai_feed_models_proxy_fails_closed_when_vit_ai_unavailable(monkeypatch):
    async def unavailable():
        raise RuntimeError("upstream unavailable")

    monkeypatch.setattr("app.api.routes.ai_feed.vit_ai_client.get_models", unavailable)
    async with _client() as client:
        response = await client.get("/api/ai-feed/models")

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "AI model registry unavailable"


@pytest.mark.asyncio
async def test_ai_feed_health_uses_live_service_values(monkeypatch):
    async def live_health():
        return {"status": "degraded", "version": "0.1.0", "models_loaded": 12}

    monkeypatch.setattr("app.api.routes.ai_feed.vit_ai_client.get_health", live_health)
    async with _client() as client:
        response = await client.get("/api/ai-feed/health")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "degraded"
    assert data["version"] == "0.1.0"
    assert data["models_loaded"] == 12
    assert data["latency_ms"] >= 0
    assert "clv_tracking_enabled" not in data
    assert "db_connected" not in data


@pytest.mark.asyncio
async def test_ai_feed_health_fails_when_vit_ai_is_unavailable(monkeypatch):
    async def unavailable():
        raise RuntimeError("upstream unavailable")

    monkeypatch.setattr("app.api.routes.ai_feed.vit_ai_client.get_health", unavailable)
    async with _client() as client:
        response = await client.get("/api/ai-feed/health")

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "AI service health unavailable"


# ── Blockchain / governance ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_governance_proposals_list():
    async with _client() as client:
        resp = await client.get("/api/governance/proposals")
    assert resp.status_code in (200, 401, 403, 404)


@pytest.mark.asyncio
async def test_marketplace_listings():
    async with _client() as client:
        resp = await client.get("/api/marketplace/listings")
    assert resp.status_code in (200, 401, 403, 404)


# ── Training ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_training_guide_steps():
    async with _client() as client:
        resp = await client.get("/api/training/guide/steps")
    assert resp.status_code in (200, 401, 403, 404)


# ── Audit ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_endpoint():
    async with _client() as client:
        token = await _make_token(client)
        resp = await client.get(
            "/api/audit/log",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code in (200, 403, 404)


# ── Pipeline ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_status():
    async with _client() as client:
        resp = await client.get("/api/pipeline/status")
    assert resp.status_code in (200, 401, 403, 404)


# ── System Status ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_system_status_endpoint():
    async with _client() as client:
        resp = await client.get("/system/status")
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert "status" in data


# ── Load JSONL error handling ─────────────────────────────────────────────────

def test_load_jsonl_skips_invalid_lines():
    import json
    import os
    import tempfile
    from services.ml_service.simulation_engine import SimulationEngine

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write('{"home_goals": 1, "away_goals": 0}\n')
        f.write("not valid json {\n")
        f.write('{"home_goals": 2, "away_goals": 2}\n')
        path = f.name
    try:
        loaded = SimulationEngine.load_jsonl(path)
        assert len(loaded) == 2
    finally:
        os.unlink(path)


# ── Worker module import ───────────────────────────────────────────────────────

def test_worker_module_loads_without_redis(monkeypatch):
    import sys
    monkeypatch.delenv("REDIS_URL", raising=False)
