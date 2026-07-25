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
