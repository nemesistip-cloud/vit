from abc import ABC, abstractmethod
from typing import Any, Dict

class ConfigProvider(ABC):
    """Abstract base class for all configuration providers."""

    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """Load configuration from the source and return as a flat dictionary."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """The priority of this provider (higher numbers take precedence)."""
        pass
