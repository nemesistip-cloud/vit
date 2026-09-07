import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from app.db.database import AsyncSessionLocal
from app.modules.storage_verification.models import ContentHashRegistry

# test_list_objects_with_data inserts rows via the module-level AsyncSessionLocal
# (bypasses conftest patch) — requires a real migrated database.
pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_list_objects_requires_authentication():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/storage/objects")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_list_objects_with_data_still_requires_authentication():
    async with AsyncSessionLocal() as db:
        content = ContentHashRegistry(
            content_hash="0xTEST_1782626733.8523111",
            content_type="text/plain",
            description="Test object",
            size_bytes=100
        )
        db.add(content)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/storage/objects")

    assert response.status_code == 401

    # Cleanup
    async with AsyncSessionLocal() as db:
        from sqlalchemy import delete
        await db.execute(delete(ContentHashRegistry).where(ContentHashRegistry.content_hash == "0xTEST_1782626733.8523111"))
        await db.commit()
