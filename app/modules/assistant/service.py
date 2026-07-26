from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass(slots=True)
class AssistantConversationContext:
    user_id: str
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AssistantProvider(Protocol):
    async def complete(self, prompt: str, context: AssistantConversationContext) -> str:
        ...


@dataclass(slots=True)
class AssistantCommand:
    name: str
    description: str
    handler: Optional[callable] = None


class GlobalAssistantService:
    """Shared assistant service that orchestrates platform capabilities through services."""

    def __init__(self, provider: Optional[AssistantProvider] = None) -> None:
        self.provider = provider
        self.commands: Dict[str, AssistantCommand] = {}
        self._service_registry: Dict[str, Any] = {}

    def register_command(self, command: AssistantCommand) -> None:
        self.commands[command.name] = command

    def register_service(self, name: str, service: Any) -> None:
        self._service_registry[name] = service

    async def ask(self, prompt: str, context: AssistantConversationContext) -> str:
        if self.provider is None:
            result = await self._orchestrate(prompt, context)
            return json.dumps(result, default=str)
        return await self.provider.complete(prompt, context)

    async def execute(self, prompt: str, context: AssistantConversationContext) -> Dict[str, Any]:
        return await self._orchestrate(prompt, context)

    async def _orchestrate(self, prompt: str, context: AssistantConversationContext) -> Dict[str, Any]:
        lower = prompt.lower()
        if "workspace" in lower and "prediction" in lower:
            return await self._handle_workspace_workflow(prompt, context)
        if "notification" in lower:
            return await self._handle_notification_workflow(prompt, context)
        if "search" in lower:
            return await self._handle_search_workflow(prompt, context)
        return {
            "status": "ok",
            "message": "Assistant received a request but no service workflow matched it yet.",
            "context": context.metadata,
        }

    async def _handle_workspace_workflow(self, prompt: str, context: AssistantConversationContext) -> Dict[str, Any]:
        workspace_name = self._extract_workspace_name(prompt) or "prediction-workspace"
        services = self._service_registry

        workspace = None
        if "identity" in services:
            workspace = getattr(services["identity"], "create_organization", None)
            if workspace is not None:
                try:
                    workspace = workspace(workspace_name, workspace_name, workspace_name.lower().replace(" ", "-"))
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
                    tags=["workspace", "assistant"],
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
            "services": [name for name in ["identity", "search", "notifications"] if name in services],
        }

    async def _handle_notification_workflow(self, prompt: str, context: AssistantConversationContext) -> Dict[str, Any]:
        services = self._service_registry
        if "notifications" not in services:
            return {"status": "ok", "action": "notify", "message": "No notification service registered"}
        notification_service = services["notifications"]
        try:
            await notification_service.publish(
                None,
                str(context.user_id),
                "Assistant update",
                prompt,
                category="system",
                priority="normal",
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

    def _extract_workspace_name(self, prompt: str) -> Optional[str]:
        match = re.search(r"['\"]([^'\"]+)['\"]", prompt)
        if match:
            return match.group(1)
        words = [w for w in re.split(r"[^a-zA-Z0-9]+", prompt) if w]
        return words[0] if words else None
