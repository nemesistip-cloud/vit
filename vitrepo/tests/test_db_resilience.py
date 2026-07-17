import pytest
import httpx
import asyncio
from unittest.mock import patch, MagicMock
from main import app

@pytest.mark.asyncio
async def test_login_retry_on_transient_error():
    """
    Test that the login endpoint retries when a transient DB error occurs.
    """

    fail_count = 0

    async def mock_execute(*args, **kwargs):
        nonlocal fail_count
        if fail_count < 1:
            fail_count += 1
            # Simulate the specific error string we are looking for
            raise Exception("asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation")

        # On 2nd attempt, return a mock result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        return mock_result

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", side_effect=mock_execute):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "Password123!"
            })

            assert fail_count == 1
            assert resp.status_code == 401

@pytest.mark.asyncio
async def test_login_eventual_failure_after_retries():
    """
    Test that the login endpoint eventually fails with 500
    if the DB remains unavailable after all retries.
    """

    fail_count = 0
    async def always_fail(*args, **kwargs):
        nonlocal fail_count
        fail_count += 1
        raise Exception("connection was closed")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", side_effect=always_fail):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "Password123!"
            })

            # After 3 attempts, it should return 500
            assert fail_count == 3
            assert resp.status_code == 500
            data = resp.json()
            assert data["error"]["code"] == "internal_error"
