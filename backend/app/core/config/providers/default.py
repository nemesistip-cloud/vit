from typing import Dict, Any
from app.core.config.providers.base import ConfigProvider

class DefaultProvider(ConfigProvider):
    """Provides default values for configuration."""

    def load(self) -> Dict[str, Any]:
        # Mostly handled by Pydantic model defaults,
        # but can be used for more complex dynamic defaults.
        return {}

    @property
    def priority(self) -> int:
        return 0
