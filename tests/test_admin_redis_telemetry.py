import pytest

from app.api.routes.admin_ops import get_infra_telemetry
from app.services import cache


class _HealthyRedis:
    async def ping(self):
        return True


@pytest.mark.asyncio
async def test_admin_infra_telemetry_reports_shared_redis(monkeypatch):
    monkeypatch.setattr(cache, "_get_redis", lambda: _HealthyRedis())

    result = await get_infra_telemetry(admin=object())

    assert result["redis_connected"] is True