import pytest

from app.modules.notifications.models import NotificationCategory, NotificationPriority, NotificationType
from app.modules.notifications.service import NotificationService


@pytest.mark.asyncio
async def test_notification_service_supports_categories_priorities_and_publish_api():
    class DummyDB:
        def __init__(self):
            self.added = []

        def add(self, item):
            self.added.append(item)

        async def commit(self):
            return None

        async def refresh(self, item):
            item.id = 42
            item.created_at = None

    db = DummyDB()
    notification = await NotificationService.create(
        db,
        1,
        NotificationType.SYSTEM,
        {},
        title="Hello",
        body="World",
        category=NotificationCategory.ACCOUNT.value,
        priority=NotificationPriority.HIGH.value,
        metadata={"source": "tests"},
    )

    assert notification.category == NotificationCategory.ACCOUNT.value
    assert notification.priority == NotificationPriority.HIGH.value
    assert notification.metadata is not None
