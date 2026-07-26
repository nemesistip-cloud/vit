from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol


@dataclass(slots=True)
class AssistantConversationContext:
    user_id: str
    session_id: Optional[str] = None
    workspace_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AssistantProvider(Protocol):
    async def complete(self, prompt: str, context: AssistantConversationContext) -> str:
        ...


@dataclass(slots=True)
class AssistantCommand:
    name: str
    description: str
    handler: Optional[callable] = None


@dataclass(slots=True)
class AssistantMessage:
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InMemoryAssistantMemory:
    """Small conversation memory abstraction for the shared AI platform."""

    def __init__(self, max_messages_per_session: int = 20) -> None:
        self.max_messages_per_session = max_messages_per_session
        self._messages: Dict[str, List[AssistantMessage]] = {}

    def session_key(self, context: AssistantConversationContext) -> str:
        session_id = context.session_id or "default"
        workspace_id = context.workspace_id or "global"
        return f"{context.user_id}:{workspace_id}:{session_id}"

    def append(self, context: AssistantConversationContext, role: str, content: str) -> None:
        key = self.session_key(context)
        messages = self._messages.setdefault(key, [])
        messages.append(AssistantMessage(role=role, content=content))
        if len(messages) > self.max_messages_per_session:
            del messages[: len(messages) - self.max_messages_per_session]

    def history(self, context: AssistantConversationContext) -> List[Dict[str, Any]]:
        return [
            {"role": message.role, "content": message.content, "timestamp": message.timestamp}
            for message in self._messages.get(self.session_key(context), [])
        ]

    def reset(self) -> None:
        self._messages.clear()


class GlobalAssistantService:
    """Shared assistant service that orchestrates platform capabilities through services."""

    def __init__(self, provider: Optional[AssistantProvider] = None, memory: Optional[InMemoryAssistantMemory] = None) -> None:
        self.provider = provider
        self.memory = memory or InMemoryAssistantMemory()
        self.commands: Dict[str, AssistantCommand] = {}
        self._service_registry: Dict[str, Any] = {}

    def register_command(self, command: AssistantCommand) -> None:
        self.commands[command.name] = command

    def register_service(self, name: str, service: Any) -> None:
        self._service_registry[name] = service

    def registered_services(self) -> List[str]:
        return sorted(self._service_registry.keys())

    def get_history(self, context: AssistantConversationContext) -> List[Dict[str, Any]]:
        return self.memory.history(context)

    async def ask(self, prompt: str, context: AssistantConversationContext) -> str:
        self.memory.append(context, "user", prompt)
        if self.provider is None:
            result = await self._orchestrate(prompt, context)
            response = json.dumps(result, default=str)
        else:
            response = await self.provider.complete(prompt, context)
        self.memory.append(context, "assistant", response)
        await self._publish_event(
            "assistant.message.completed",
            {"user_id": context.user_id, "workspace_id": context.workspace_id, "session_id": context.session_id},
        )
        return response

    async def execute(self, prompt: str, context: AssistantConversationContext) -> Dict[str, Any]:
        self.memory.append(context, "user", prompt)
        result = await self._orchestrate(prompt, context)
        self.memory.append(context, "assistant", json.dumps(result, default=str))
        await self._publish_event(
            "assistant.command.executed",
            {
                "user_id": context.user_id,
                "workspace_id": context.workspace_id,
                "session_id": context.session_id,
                "action": result.get("action"),
                "status": result.get("status"),
            },
        )
        return result

    async def _orchestrate(self, prompt: str, context: AssistantConversationContext) -> Dict[str, Any]:
        lower = prompt.lower()
        command = await self._try_command(prompt)
        if command is not None:
            return command
        if "workspace" in lower and "prediction" in lower:
            return await self._handle_workspace_workflow(prompt, context)
        if "notification" in lower or "notify" in lower:
            return await self._handle_notification_workflow(prompt, context)
        if "search" in lower or "find" in lower:
            return await self._handle_search_workflow(prompt, context)
        return {
            "status": "ok",
            "action": "assistant_reply",
            "message": "Assistant received a request but no service workflow matched it yet.",
            "context": {
                "workspace_id": context.workspace_id,
                "roles": context.roles,
                "metadata": context.metadata,
            },
            "history_size": len(self.memory.history(context)),
            "services": self.registered_services(),
        }

    async def _try_command(self, prompt: str) -> Optional[Dict[str, Any]]:
        services = self._service_registry
        command_registry = services.get("commands")
        if command_registry is None:
            return None

        normalized = prompt.strip().lower()
        command_name = None
        if normalized.startswith("/"):
            command_name = normalized[1:].split()[0]
        elif normalized.startswith("run "):
            command_name = normalized.split(maxsplit=1)[1].split()[0]
        elif "open ai" in normalized:
            command_name = "open_ai"
        elif "open storage" in normalized:
            command_name = "open_storage"
        elif "open wallet" in normalized:
            command_name = "open_wallet"

        if not command_name:
            return None

        try:
            result = command_registry.execute(command_name)
            if inspect.isawaitable(result):
                result = await result
            return {"status": "ok", "action": "execute_command", "command": command_name, "result": result}
        except Exception as exc:
            return {"status": "error", "action": "execute_command", "command": command_name, "message": str(exc)}

    async def _handle_workspace_workflow(self, prompt: str, context: AssistantConversationContext) -> Dict[str, Any]:
        workspace_name = self._extract_workspace_name(prompt) or "prediction-workspace"
        services = self._service_registry

        workspace = None
        if "identity" in services:
            workspace_factory = getattr(services["identity"], "create_organization", None)
            if workspace_factory is not None:
                try:
                    workspace = workspace_factory(workspace_name, workspace_name, workspace_name.lower().replace(" ", "-"))
                    if inspect.isawaitable(workspace):
                        workspace = await workspace
                except TypeError:
                    workspace = None

        if "search" in services and workspace is not None:
            search = services["search"]
            try:
                search.index_resource(
                    resource_type="workspaces",
                    resource_id=str(getattr(workspace, "id", workspace_name)),
                    title=workspace_name,
                    description="Workspace created by the global assistant",
                    tags=["workspace", "assistant", "prediction"],
                    owner=str(context.user_id),
                    permissions=["read", "write"],
                )
            except Exception:
                pass

        if "notifications" in services:
            notification_service = services["notifications"]
            try:
                if hasattr(notification_service, "publish"):
                    await notification_service.publish(
                        None,
                        str(context.user_id),
                        "Workspace ready",
                        f"Workspace '{workspace_name}' is ready.",
                        category="account",
                        priority="high",
                    )
                elif hasattr(notification_service, "send"):
                    from app.modules.notifications.framework import NotificationEnvelope

                    await notification_service.send(
                        NotificationEnvelope(
                            channel="in_app",
                            recipient=str(context.user_id),
                            title="Workspace ready",
                            body=f"Workspace '{workspace_name}' is ready.",
                        )
                    )
            except Exception:
                pass

        return {
            "status": "ok",
            "action": "create_workspace",
            "workspace": {
                "name": workspace_name,
                "id": getattr(workspace, "id", workspace_name),
                "owner": context.user_id,
            },
            "services": [name for name in ["identity", "search", "notifications", "events", "commands"] if name in services],
        }

    async def _handle_notification_workflow(self, prompt: str, context: AssistantConversationContext) -> Dict[str, Any]:
        services = self._service_registry
        if "notifications" not in services:
            return {"status": "ok", "action": "notify", "message": "No notification service registered"}
        notification_service = services["notifications"]
        try:
            if hasattr(notification_service, "publish"):
                await notification_service.publish(
                    None,
                    str(context.user_id),
                    "Assistant update",
                    prompt,
                    category="system",
                    priority="normal",
                )
            else:
                from app.modules.notifications.framework import NotificationEnvelope

                await notification_service.send(
                    NotificationEnvelope(channel="in_app", recipient=str(context.user_id), title="Assistant update", body=prompt)
                )
        except Exception as exc:
            return {"status": "error", "message": str(exc)}
        return {"status": "ok", "action": "notify", "message": "Notification published"}

    async def _handle_search_workflow(self, prompt: str, context: AssistantConversationContext) -> Dict[str, Any]:
        services = self._service_registry
        if "search" not in services:
            return {"status": "ok", "action": "search", "message": "No search service registered"}
        search = services["search"]
        query = re.sub(r"\b(search|find|look up)\b", "", prompt, flags=re.I).strip()
        results = search.search(query or "platform", limit=5)
        return {
            "status": "ok",
            "action": "search",
            "query": query or "platform",
            "results": [
                {"title": item.title, "resource_type": getattr(item, "resource_type", None), "resource_id": getattr(item, "resource_id", None)}
                for item in results
            ],
        }

    async def _publish_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        events = self._service_registry.get("events")
        if events is None or not hasattr(events, "publish"):
            return
        try:
            await events.publish(event_name, payload, sender="assistant.service", max_retries=0)
        except Exception:
            return

    def _extract_workspace_name(self, prompt: str) -> Optional[str]:
        match = re.search(r"['\"]([^'\"]+)['\"]", prompt)
        if match:
            return match.group(1)
        words = [w for w in re.split(r"[^a-zA-Z0-9]+", prompt) if w]
        return words[0] if words else None
