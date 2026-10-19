"""Core dependency injection helpers for VIT, loaded only when requested."""

from importlib import import_module
from typing import Any

_DEPENDENCY_EXPORTS = {
    "get_orchestrator",
    "get_orchestrator_dep",
    "get_data_loader",
    "get_data_loader_dep",
    "get_telegram_alerts",
    "get_telegram_dep",
}

__all__ = sorted(_DEPENDENCY_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _DEPENDENCY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    dependencies = import_module(".dependencies", __name__)
    value = getattr(dependencies, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | _DEPENDENCY_EXPORTS)
