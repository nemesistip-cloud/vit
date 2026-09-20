import json
from unittest.mock import patch

import pytest

import app.services.web_search as web_search


@pytest.mark.asyncio
async def test_google_search_uses_platform_config_when_env_missing(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_SEARCH_ENGINE_ID", raising=False)

    async def fake_lookup(key: str):
        if key == "GOOGLE_API_KEY":
            return "db-google-key"
        if key == "GOOGLE_SEARCH_ENGINE_ID":
            return "db-search-engine"
        return ""

    with patch.object(web_search, "_get_admin_config_value", side_effect=fake_lookup):
        class FakeResponse:
            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            @property
            def json(self):
                return self._payload

        captured = {}

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, url, params=None, timeout=None, headers=None):
                captured["url"] = url
                captured["params"] = params
                return FakeResponse({"items": [{"snippet": "Admin-config snippet"}]})

        monkeypatch.setattr(web_search.httpx, "AsyncClient", FakeAsyncClient)

        results = await web_search._google_search("Arsenal injury news", max_results=2)

    assert results == ["Admin-config snippet"]
    assert captured["params"]["key"] == "db-google-key"
    assert captured["params"]["cx"] == "db-search-engine"


@pytest.mark.asyncio
async def test_google_search_uses_custom_search_when_configured(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "test-search-engine")

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        @property
        def json(self):
            return self._payload

    captured = {}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None, timeout=None, headers=None):
            captured["url"] = url
            captured["params"] = params
            return FakeResponse({
                "items": [
                    {"snippet": "Google snippet one"},
                    {"snippet": "Google snippet two"},
                ]
            })

    monkeypatch.setattr(web_search.httpx, "AsyncClient", FakeAsyncClient)

    results = await web_search._google_search("Arsenal injury news", max_results=2)

    assert results == ["Google snippet one", "Google snippet two"]
    assert captured["url"] == "https://www.googleapis.com/customsearch/v1"
    assert captured["params"]["key"] == "test-google-key"
    assert captured["params"]["cx"] == "test-search-engine"
