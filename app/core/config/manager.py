import logging
import os
import json
from typing import Dict, Any, List, Optional, Type
from pydantic import ValidationError

from app.core.config.models import VITConfig, AppConfig, DatabaseConfig, RedisConfig, AIConfig, BlockchainConfig, ExternalServicesConfig, TachyonConfig
from app.core.config.providers.base import ConfigProvider
from app.core.config.providers.env import EnvProvider
from app.core.config.providers.default import DefaultProvider
from app.core.config.secrets import secrets_manager
from app.core.config.feature_flags import feature_flag_manager

logger = logging.getLogger(__name__)

class ConfigurationManager:
    """
    The central authority for all VIT Ecosystem configuration.
    Orchestrates resolution, validation, and access.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigurationManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._config: Optional[VITConfig] = None
        self._providers: List[ConfigProvider] = [
            DefaultProvider(),
            EnvProvider()
        ]
        self._initialized = True

    async def load(self):
        """Perform the full configuration loading and validation sequence."""
        logger.info("[config] Loading VIT Configuration...")

        # 1. Collect data from all providers
        raw_data: Dict[str, Any] = {}
        # Sort providers by priority
        sorted_providers = sorted(self._providers, key=lambda p: p.priority)
        for provider in sorted_providers:
            raw_data.update(provider.load())

        # 2. Resolve secrets
        raw_data = await secrets_manager.resolve_secrets(raw_data)

        # 3. Initialize feature flags
        feature_flag_manager.initialize(raw_data)

        # 4. Map raw data to section models
        try:
            # We use the alias (original env var name) for mapping
            app_data = self._filter_data_by_alias(AppConfig, raw_data)
            db_data = self._filter_data_by_alias(DatabaseConfig, raw_data)
            redis_data = self._filter_data_by_alias(RedisConfig, raw_data)
            ai_data = self._filter_data_by_alias(AIConfig, raw_data)
            bc_data = self._filter_data_by_alias(BlockchainConfig, raw_data)
            ext_data = self._filter_data_by_alias(ExternalServicesConfig, raw_data)
            tachyon_data = self._filter_data_by_alias(TachyonConfig, raw_data)

            self._config = VITConfig(
                app=AppConfig(**app_data),
                db=DatabaseConfig(**db_data),
                redis=RedisConfig(**redis_data),
                ai=AIConfig(**ai_data),
                blockchain=BlockchainConfig(**bc_data),
                external=ExternalServicesConfig(**ext_data),
                tachyon=TachyonConfig(**tachyon_data),
                feature_flags=feature_flag_manager.get_all_flags()
            )
            logger.info(f"[config] Configuration validated successfully for {self._config.app.environment.value}")
        except ValidationError as e:
            logger.critical(f"[config] Configuration validation failed: \n{e}")
            raise SystemExit(1)
        except Exception as e:
            logger.critical(f"[config] Unexpected error during configuration load: {e}")
            raise SystemExit(1)

    def _filter_data_by_alias(self, model: Type[Any], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Filters raw data to match the aliases defined in the model."""
        filtered = {}
        for field_name, field in model.__fields__.items():
            alias = field.alias
            if alias in raw_data:
                filtered[alias] = raw_data[alias]
        return filtered

    @property
    def config(self) -> VITConfig:
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._config

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return non-sensitive configuration diagnostics."""
        if not self._config:
            return {"status": "not_loaded"}

        return {
            "status": "loaded",
            "environment": self._config.app.environment.value,
            "version": self._config.app.version,
            "effective_config": secrets_manager.redact(self._config),
            "feature_flags": feature_flag_manager.get_all_flags(),
            "providers": [p.__class__.__name__ for p in self._providers],
            "missing_required_keys": self._get_missing_required_keys()
        }

    def _get_missing_required_keys(self) -> List[str]:
        """Check for potentially missing optional keys that are commonly used."""
        missing = []
        if not self._config: return missing

        # Check some key fields
        if not self._config.ai.isports_api_key: missing.append("ISPORTS_API_KEY")
        if not self._config.external.paystack_secret_key: missing.append("PAYSTACK_SECRET_KEY")
        if not self._config.external.resend_api_key: missing.append("RESEND_API_KEY")

        return missing

    def export_effective_config(self, path: str):
        """Export redacted effective configuration to a JSON file."""
        if not self._config:
            return

        redacted = secrets_manager.redact(self._config)
        with open(path, 'w') as f:
            json.dump(redacted, f, indent=2)
        logger.info(f"[config] Exported effective config to {path}")

# Global Configuration Manager Singleton
config_manager = ConfigurationManager()
