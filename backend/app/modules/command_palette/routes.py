from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Query

from app.modules.command_palette.registry import CommandRegistry

router = APIRouter(prefix="/api/platform/commands", tags=["Platform Commands"])

_registry = CommandRegistry()


def get_registry() -> CommandRegistry:
    return _registry


@router.get("", summary="List registered platform commands")
def list_commands() -> Dict[str, Any]:
    commands = [
        {"name": definition.name, "description": definition.description}
        for definition in _registry._commands.values()
    ]
    return {"commands": commands, "total": len(commands)}


@router.get("/search", summary="Search registered commands")
def search_commands(q: str = Query(..., min_length=1)) -> Dict[str, Any]:
    normalized = q.lower().strip()
    matches = [
        {"name": definition.name, "description": definition.description}
        for definition in _registry._commands.values()
        if normalized in definition.name.lower() or normalized in definition.description.lower()
    ]
    return {"commands": matches, "total": len(matches)}


@router.post("/{name}", summary="Execute a registered command")
def execute_command(name: str) -> Dict[str, Any]:
    definition = _registry.get(name)
    if definition is None:
        return {"error": "unknown_command", "message": f"Command '{name}' is not registered"}
    result = definition.handler()
    return {"name": name, "result": result}


# Register default platform commands when this module is imported.
def _register_defaults() -> None:
    if _registry.get("open_wallet") is None:
        _registry.register("open_wallet", "Open wallet", lambda: "wallet")
    if _registry.get("open_storage") is None:
        _registry.register("open_storage", "Open storage", lambda: "storage")
    if _registry.get("open_ai") is None:
        _registry.register("open_ai", "Open AI", lambda: "ai")
    if _registry.get("create_prediction") is None:
        _registry.register("create_prediction", "Create prediction", lambda: "prediction")
    if _registry.get("upload_file") is None:
        _registry.register("upload_file", "Upload file", lambda: "upload")
    if _registry.get("search_user") is None:
        _registry.register("search_user", "Search user", lambda: "search")
    if _registry.get("notifications") is None:
        _registry.register("notifications", "Open notifications", lambda: "notifications")


_register_defaults()
