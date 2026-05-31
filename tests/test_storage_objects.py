import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from app.db.database import AsyncSessionLocal
from app.modules.storage_verification.models import ContentHashRegistry

@pytest.mark.asyncio
async def test_list_objects_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/objects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_list_objects_with_data():
    async with AsyncSessionLocal() as db:
        content = ContentHashRegistry(
            content_hash="0xTEST",
            content_type="text/plain",
            description="Test object",
            size_bytes=100
        )
        db.add(content)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/objects")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(obj["content_hash"] == "0xTEST" for obj in data)

    # Cleanup
    async with AsyncSessionLocal() as db:
        from sqlalchemy import delete
        await db.execute(delete(ContentHashRegistry).where(ContentHashRegistry.content_hash == "0xTEST"))
        await db.commit()
