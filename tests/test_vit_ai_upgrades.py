import pytest
import asyncio
from httpx import AsyncClient

from main import app
from app.services.vit_ai_client import VitAIClient, CircuitBreakerOpenException
from app.modules.ai.gateway import AIGateway
from app.modules.ai.routes import router as ai_module_router

# Mark all tests as requiring asyncio/pytest-asyncio
pytestmark = pytest.mark.asyncio

# Eagerly register actual modules AI routes onto the app instance
try:
    app.include_router(ai_module_router)
except Exception:
    pass

async def test_ai_engine_status(client: AsyncClient, db_session):
    """Verify registry status and metadata output."""
    response = await client.get("/api/ai-engine/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "registry_total" in data

async def test_list_models_registry(client: AsyncClient, db_session):
    """Verify registry returns upgraded fields (token limit, capabilities, etc.)."""
    response = await client.get("/api/ai-engine/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert isinstance(data["models"], list)
    if len(data["models"]) > 0:
        first = data["models"][0]
        assert "token_limit" in first
        assert "pricing_metadata" in first
        assert "capabilities" in first
        assert "endpoint" in first

async def test_hot_register_duplicate_fails(client: AsyncClient, db_session):
    """Verify hot registration duplicate prevention."""
    payload = {
        "key": "xgb_v2",
        "name": "Duplicate XGBoost",
        "model_type": "XGBoost",
        "supported_markets": ["1x2"]
    }
    # First, make sure the models are bootstrapped so xgb_v2 exists
    await client.get("/api/ai-engine/models")

    response = await client.post("/api/ai-engine/models/register", json=payload)
    assert response.status_code == 400
    body = response.json()
    # Support either legacy FastAPI HTTPException detail or the app's wrapped error
    detail_msg = body.get("detail") or body.get("error", {}).get("message", "")
    assert "already registered" in detail_msg

async def test_ai_gateway_routing_manual():
    """Verify AI Gateway manual routing fallback."""
    gw = AIGateway()
    res = await gw.route_chat("Explain blockchain consensus", routing_mode="manual", manual_model_id="llm_consensus_v1")
    assert res["status"] == "success"
    assert res["model_id"] == "llm_consensus_v1"
    assert "response" in res

async def test_ai_gateway_routing_fastest():
    """Verify AI Gateway fastest routing mode directs to local direct model."""
    gw = AIGateway()
    res = await gw.route_chat("Match forecast query", routing_mode="fastest")
    assert res["status"] == "success"
    assert res["model_id"] == "xgb_v2"
    assert "response" in res

async def test_vit_ai_client_circuit_breaker():
    """Verify VitAIClient circuit breaker states."""
    c = VitAIClient()
    # Force state to closed and reset failures
    c.state = "CLOSED"
    c.failure_count = 0

    # Check circuit is verified closed
    c._check_circuit()

    # Force failure to trigger circuit open
    for _ in range(c.failure_threshold):
        c._record_failure()

    assert c.state == "OPEN"
    with pytest.raises(CircuitBreakerOpenException):
        c._check_circuit()

    # Reset circuit breaker
    c._record_success()
    assert c.state == "CLOSED"
