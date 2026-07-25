from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.event_bus import event_bus
from app.modules.assistant.service import AssistantConversationContext, GlobalAssistantService
from app.modules.command_palette.registry import CommandRegistry
from app.modules.identity.service import IdentityService
from app.modules.notifications.framework import NotificationEnvelope, NotificationService as PlatformNotificationService
from app.modules.search.foundation import GlobalSearchService, SearchDocument


class PlatformIntegrationService:
    """Operational wiring for the Phase 2.1 platform foundation services."""

    def __init__(self) -> None:
        self.identity = IdentityService()
        self.events = event_bus
        self.notifications = PlatformNotificationService()
        self.search = GlobalSearchService()
        self.assistant = GlobalAssistantService()
        self.commands = CommandRegistry()
        self._registered = False

    def register_defaults(self) -> None:
        if self._registered:
            return
        self.commands.register("open_wallet", "Open wallet", lambda: "wallet")
        self.commands.register("open_storage", "Open storage", lambda: "storage")
        self.commands.register("open_ai", "Open AI", lambda: "ai")
        self.commands.register("create_prediction", "Create prediction", lambda: "prediction")
        self.commands.register("upload_file", "Upload file", lambda: "upload")
        self.commands.register("search_user", "Search user", lambda: "search")
        self.commands.register("open_governance", "Open governance", lambda: "governance")
        self.commands.register("settings", "Open settings", lambda: "settings")
        self.commands.register("notifications", "Open notifications", lambda: "notifications")

        self.notifications.register_channel("in_app", self._NoopChannel())
        self.notifications.register_channel("email", self._NoopChannel())
        self.notifications.register_channel("push", self._NoopChannel())
        self._registered = True

    async def index_entity(self, collection: str, entity_id: str, title: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.search.index_document(
            SearchDocument(
                collection=collection,
                document_id=entity_id,
                title=title,
                content=content,
                metadata=metadata or {},
            )
        )

    async def create_assistant_context(self, user_id: str, session_id: Optional[str] = None) -> AssistantConversationContext:
        return AssistantConversationContext(user_id=user_id, session_id=session_id)

    async def publish_notification(self, user_id: str, title: str, body: str, channel: str = "in_app") -> None:
        await self.notifications.send(
            NotificationEnvelope(channel=channel, recipient=user_id, title=title, body=body)
        )

    class _NoopChannel:
        async def send(self, recipient: str, title: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> None:
            return None


platform_integration = PlatformIntegrationService()
platform_integration.register_defaults()
