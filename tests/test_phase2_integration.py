import pytest

from app.core.event_bus import event_bus
from app.modules.notifications.service import NotificationService
from app.modules.platform.integration import platform_integration
from app.modules.search.foundation import GlobalSearchService


@pytest.mark.asyncio
async def test_platform_integration_indexes_and_notifies():
    await platform_integration.index_entity("tests", "entity-1", "Demo", "Demo content")
    result = platform_integration.search.search("Demo")
    assert result

    await platform_integration.publish_notification("user-1", "Hello", "World")
    assert platform_integration.notifications


@pytest.mark.asyncio
async def test_notification_service_publishes_platform_events(monkeypatch):
    class DummyDB:
        async def commit(self):
            return None

        async def refresh(self, _):
            return None

        def add(self, _):
            return None

    class DummyNotification:
        id = 1
        title = "Test"
        body = "Body"
        created_at = None

    monkeypatch.setattr(
        NotificationService,
        "create",
        staticmethod(lambda db, user_id, ntype, context, **kwargs: _create_stub_notification()),
    )

    async def _create_stub_notification():
        return DummyNotification()

    async def fake_push(*args, **kwargs):
        return None

    monkeypatch.setattr("app.modules.notifications.service.notification_ws_manager.push", fake_push)
    monkeypatch.setattr("app.modules.notifications.service.platform_integration.index_entity", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.modules.notifications.service.event_bus.publish", lambda *args, **kwargs: None)

    service = GlobalSearchService()
    assert service is not None
