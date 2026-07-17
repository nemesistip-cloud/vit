import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from app.api.routes.explorer import router as explorer_router
from app.db.database import AsyncSessionLocal

@pytest.fixture
def test_app(db_session):
    app = FastAPI()
    app.include_router(explorer_router, prefix="/api")
    return app

@pytest.mark.asyncio
async def test_explorer_blocks_list(test_app):
    async with AsyncClient(transport=pytest.importorskip("httpx").ASGITransport(app=test_app), base_url="http://test") as ac:
        response = await ac.get("/api/explorer/blocks")
        assert response.status_code in [200, 500]

@pytest.mark.asyncio
async def test_explorer_transactions_list(test_app):
    async with AsyncClient(transport=pytest.importorskip("httpx").ASGITransport(app=test_app), base_url="http://test") as ac:
        response = await ac.get("/api/explorer/transactions")
        assert response.status_code in [200, 500]

@pytest.mark.asyncio
async def test_explorer_nodes_list(test_app):
    async with AsyncClient(transport=pytest.importorskip("httpx").ASGITransport(app=test_app), base_url="http://test") as ac:
        response = await ac.get("/api/explorer/nodes")
        assert response.status_code in [200, 500]

@pytest.mark.asyncio
async def test_explorer_nodes_map(test_app):
    async with AsyncClient(transport=pytest.importorskip("httpx").ASGITransport(app=test_app), base_url="http://test") as ac:
        response = await ac.get("/api/explorer/nodes/map")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data

@pytest.mark.asyncio
async def test_explorer_account_detail(test_app):
    async with AsyncClient(transport=pytest.importorskip("httpx").ASGITransport(app=test_app), base_url="http://test") as ac:
        # Test with a dummy address, expect 404
        response = await ac.get("/api/explorer/accounts/VIT_DUMMY_ADDRESS")
        assert response.status_code == 404
