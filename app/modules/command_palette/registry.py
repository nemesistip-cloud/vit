from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass(slots=True)
class CommandDefinition:
    name: str
    description: str
    handler: Callable[[], object]


class CommandRegistry:
    """Central registry for shared platform commands."""

    def __init__(self) -> None:
        self._commands: Dict[str, CommandDefinition] = {}

    def register(self, name: str, description: str, handler: Callable[[], object]) -> CommandDefinition:
        definition = CommandDefinition(name=name, description=description, handler=handler)
        self._commands[name] = definition
        return definition

    def get(self, name: str) -> Optional[CommandDefinition]:
        return self._commands.get(name)

    def execute(self, name: str) -> object:
        definition = self.get(name)
        if definition is None:
            raise KeyError(f"Unknown command: {name}")
        return definition.handler()
