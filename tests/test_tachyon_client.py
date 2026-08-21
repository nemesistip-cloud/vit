import pytest

from app.services import tachyon_client as module


class _Response:
    status_code = 200

    def json(self):
        return {
            "status": "operational",
            "active_nodes": 3,
            "provider_breakdown": {"Disk": 3},
        }


@pytest.mark.asyncio
async def test_health_uses_status_contract(monkeypatch):
    async def fake_request(method, path, **kwargs):
        assert method == "GET"
        assert path == "/status"
        return _Response()

    monkeypatch.setattr(module, "_request", fake_request)
    result = await module.TachyonClient().health()

    assert result["status"] == "operational"
    assert result["nodes"]["Disk"]["ok"] is True


@pytest.mark.asyncio
async def test_gc_reports_unsupported_contract():
    result = await module.TachyonClient().gc()

    assert result["status"] == "unsupported"
    assert result["orphans_removed"] == 0