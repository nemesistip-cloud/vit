import os
from typing import Dict, Any
from app.core.config.providers.base import ConfigProvider

class EnvProvider(ConfigProvider):
    """Loads configuration from environment variables."""

    def load(self) -> Dict[str, Any]:
        return dict(os.environ)

    @property
    def priority(self) -> int:
        return 100
