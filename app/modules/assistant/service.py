from __future__ import annotations

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
    """Shared assistant service used by platform modules."""

    def __init__(self, provider: Optional[AssistantProvider] = None) -> None:
        self.provider = provider
        self.commands: Dict[str, AssistantCommand] = {}

    def register_command(self, command: AssistantCommand) -> None:
        self.commands[command.name] = command

    async def ask(self, prompt: str, context: AssistantConversationContext) -> str:
        if self.provider is None:
            return "Assistant provider not configured"
        return await self.provider.complete(prompt, context)
