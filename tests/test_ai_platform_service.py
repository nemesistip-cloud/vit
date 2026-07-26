import json

import pytest

from app.core.event_bus import event_bus
from app.modules.assistant.service import AssistantConversationContext, GlobalAssistantService
from app.modules.command_palette.registry import CommandRegistry
from app.modules.platform.integration import platform_integration
from app.modules.search.foundation import GlobalSearchService, SearchDocument


@pytest.mark.asyncio
async def test_global_assistant_uses_commands_memory_and_events():
    event_bus.reset_state()
    received = []

    async def handler(event):
        received.append(event.payload)

    event_bus.subscribe("assistant.command.executed", handler)

    commands = CommandRegistry()
    commands.register("open_ai", "Open AI", lambda: "ai")

    assistant = GlobalAssistantService()
    assistant.register_service("commands", commands)
    assistant.register_service("events", event_bus)

    context = AssistantConversationContext(user_id="user-1", session_id="session-1", workspace_id="workspace-1")
    result = await assistant.execute("open ai", context)

    assert result == {"status": "ok", "action": "execute_command", "command": "open_ai", "result": "ai"}
    assert len(assistant.get_history(context)) == 2
    assert received[0]["action"] == "execute_command"
    assert received[0]["workspace_id"] == "workspace-1"


@pytest.mark.asyncio
async def test_global_assistant_searches_shared_platform_index():
    search = GlobalSearchService()
    search.reset()
    search.index_document(
        SearchDocument(
            collection="docs",
            document_id="ai-platform",
            title="Global AI Platform",
            content="Shared assistant service for VIT workspaces",
        )
    )

    assistant = GlobalAssistantService()
    assistant.register_service("search", search)

    context = AssistantConversationContext(user_id="user-2", session_id="session-2")
    result = await assistant.execute("search global ai", context)

    assert result["status"] == "ok"
    assert result["action"] == "search"
    assert any(item["title"] == "Global AI Platform" for item in result["results"])


@pytest.mark.asyncio
async def test_platform_integration_wires_assistant_to_shared_services():
    context = await platform_integration.create_assistant_context("user-3", session_id="session-3")
    response = await platform_integration.assistant.ask("open wallet", context)
    payload = json.loads(response)

    assert {"commands", "events", "identity", "notifications", "search"}.issubset(
        set(platform_integration.assistant.registered_services())
    )
    assert payload["action"] == "execute_command"
    assert payload["command"] == "open_wallet"
