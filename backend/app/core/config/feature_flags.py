import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class FeatureFlagManager:
    """Manages runtime feature flags with environment-specific defaults."""

    def __init__(self):
        self._flags: Dict[str, bool] = {}

    def initialize(self, config_data: Dict[str, Any]):
        """Load flags from config data (populated from Env/Files/etc)."""
        # Look for keys prefixed with FF_ or FEATURE_
        for k, v in config_data.items():
            if k.startswith("FF_") or k.startswith("FEATURE_"):
                self._flags[k] = str(v).lower() in ("true", "1", "yes")

        logger.debug(f"[feature_flags] Initialized {len(self._flags)} flags")

    def is_enabled(self, flag: str, default: bool = False) -> bool:
        """Check if a feature flag is enabled."""
        return self._flags.get(flag, self._flags.get(f"FF_{flag}", self._flags.get(f"FEATURE_{flag}", default)))

    def set_flag(self, flag: str, enabled: bool):
        """Manually override a flag at runtime."""
        self._flags[flag] = enabled

    def get_all_flags(self) -> Dict[str, bool]:
        """Return a copy of all current flags."""
        return self._flags.copy()

feature_flag_manager = FeatureFlagManager()
