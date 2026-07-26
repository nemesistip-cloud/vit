import pytest

from app.core.event_bus import event_bus
from app.modules.events.bus import EventBus, UserRegistered
from app.modules.command_palette.registry import CommandRegistry
from app.modules.search.foundation import GlobalSearchService, SearchDocument


def test_event_bus_dispatches_typed_events():
    bus = EventBus()
    received = []

    def handler(event: UserRegistered) -> None:
        received.append(event.user_id)

    bus.subscribe(UserRegistered, handler)
    bus.publish(UserRegistered(user_id="u-1", email="user@example.com"))

    assert received == ["u-1"]


def test_command_registry_executes_registered_commands():
    registry = CommandRegistry()

    def greet() -> str:
        return "ok"

    registry.register("greet", "says ok", greet)
    result = registry.execute("greet")

    assert result == "ok"


def test_search_service_indexes_and_finds_documents():
    service = GlobalSearchService()
    service.reset()
    service.index_document(
        SearchDocument(
            collection="users",
            document_id="user-1",
            title="Ada Lovelace",
            content="platform administrator",
        )
    )

    results = service.search("administrator", collection="users")

    assert results[0].document_id == "user-1"


@pytest.mark.asyncio
async def test_search_service_supports_platform_resources_and_event_driven_indexing():
    service = GlobalSearchService()
    service.reset()

    service.index_resource(
        resource_type="users",
        resource_id="user-1",
        title="Ada Lovelace",
        description="Platform administrator and researcher",
        tags=["admin", "research"],
        owner="owner-1",
        permissions=["read", "write"],
        last_updated="2026-07-26T00:00:00Z",
    )

    results = service.search("admin", resource_type="users", tags=["admin"], limit=10)
    assert results[0].resource_id == "user-1"
    assert results[0].resource_type == "users"
    assert results[0].search_score > 0

    await event_bus.publish(
        "user.registered",
        {"user_id": "user-2", "email": "ada@vit.network"},
        sender="tests",
    )

    indexed = service.search("user-2", resource_type="users", limit=10)
    assert any(item.resource_id == "user-2" for item in indexed)
