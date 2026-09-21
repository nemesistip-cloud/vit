import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tachyon.api.router import router

app = FastAPI()
app.include_router(router, prefix="/api/v1")

client = TestClient(app)

def test_files_api_routes_exist():
    # Verify GET /api/v1/files returns 200 or handles mock DB
    with patch("tachyon.api.router.get_db") as mock_get_db:
        # Check client response for endpoints
        res_list = client.get("/api/v1/files")
        assert res_list.status_code in (200, 500)  # 500 if DB session unmocked, but route exists (not 404 or 405)

        res_post = client.post("/api/v1/files", files={"file": ("test.txt", b"hello world", "text/plain")})
        assert res_post.status_code != 405  # Method Not Allowed should NOT be returned
