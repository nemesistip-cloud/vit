import logging
    import os
    from typing import Any, Dict, List, Optional, Type

    from pydantic import ValidationError

    from app.core.config.models import (
        AIConfig,
        AppConfig,
        BlockchainConfig,
        DatabaseConfig,
        ExternalServicesConfig,
        RedisConfig,
        TachyonConfig,
        VITConfig,
    )
    from app.core.config.providers.base import ConfigProvider
    from app.core.config.providers.default import DefaultProvider
    from app.core.config.providers.env import EnvProvider
    from app.core.config.feature_flags import feature_flag_manager
    from app.core.config.secrets import secrets_manager

    logger = logging.getLogger(__name__)


    class ConfigurationManager:
        """
        Central authority for all VIT Ecosystem configuration.

        Key contract: load() NEVER raises.  On any error it logs CRITICAL,
        sets boot_error, and continues with safe defaults so Render's
        health-check (GET /ping) still returns 200 and the service starts.

        Supports Pydantic v1 (model.__fields__) and v2 (model.model_fields).
        """

        _instance: Optional["ConfigurationManager"] = None

        def __new__(cls) -> "ConfigurationManager":
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

        def __init__(self) -> None:
            if self._initialized:
                return
            self._config: Optional[VITConfig] = None
            self._boot_error: Optional[str] = None
            self._providers: List[ConfigProvider] = [DefaultProvider(), EnvProvider()]
            self._initialized = True

        # ── Public API ─────────────────────────────────────────────────────────

        @property
        def boot_error(self) -> Optional[str]:
            """Human-readable error if load() failed; None when healthy."""
            return self._boot_error

        @property
        def is_healthy(self) -> bool:
            return self._boot_error is None and self._config is not None

        @property
        def config(self) -> VITConfig:
            """Always returns a VITConfig; falls back to defaults if load() failed."""
            if self._config is None:
                self._config = self._make_default_config()
            return self._config

        async def load(self) -> None:
            """
            Full configuration loading and validation sequence.
            Guaranteed not to raise — on any error logs CRITICAL and uses safe defaults.
            """
            logger.info("[config] Loading VIT Configuration...")
            try:
                raw = self._collect_raw_data()
                raw = await self._resolve_secrets_safe(raw)
                feature_flag_manager.initialize(raw)
                self._config = self._build_config(raw)
                env_val = getattr(
                    self._config.app.environment, "value",
                    str(self._config.app.environment),
                )
                logger.info("[config] Configuration loaded — environment=%s", env_val)

            except ValidationError as exc:
                self._boot_error = f"Pydantic ValidationError: {exc}"
                logger.critical(
                    "[config] Validation failed — starting with safe defaults.\n%s",
                    exc, exc_info=True,
                )
                self._config = self._make_default_config()

            except Exception as exc:  # noqa: BLE001
                self._boot_error = f"Unexpected config error: {exc}"
                logger.critical(
                    "[config] Unexpected error — starting with safe defaults.\n%s",
                    exc, exc_info=True,
                )
                self._config = self._make_default_config()

        # ── Backward-compatible flat access ────────────────────────────────────

        def get(self, key: str, default: Any = None) -> Any:
            for section in (
                self.config.app, self.config.db, self.config.redis, self.config.ai,
                self.config.blockchain, self.config.external, self.config.tachyon,
            ):
                if hasattr(section, key):
                    return getattr(section, key)
            return default

        def get_database_url(self) -> str:
            url = self.config.db.url
            return url or os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./vit.db")

        # ── Diagnostics ────────────────────────────────────────────────────────

        def get_diagnostics(self) -> Dict[str, Any]:
            missing = [
                k for k in ("ISPORTS_API_KEY", "PAYSTACK_SECRET_KEY", "RESEND_API_KEY")
                if not os.getenv(k)
            ]
            return {
                "healthy": self.is_healthy,
                "boot_error": self._boot_error,
                "missing_optional_keys": missing,
                "environment": (
                    getattr(
                        self._config.app.environment, "value",
                        str(self._config.app.environment),
                    )
                    if self._config else "unknown"
                ),
            }

        # ── Private helpers ────────────────────────────────────────────────────

        def _collect_raw_data(self) -> Dict[str, Any]:
            raw: Dict[str, Any] = {}
            for provider in sorted(self._providers, key=lambda p: p.priority):
                raw.update(provider.load())
            return raw

        async def _resolve_secrets_safe(self, raw: Dict[str, Any]) -> Dict[str, Any]:
            try:
                return await secrets_manager.resolve_secrets(raw)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[config] Secret resolution failed (env-only): %s", exc)
                return raw

        def _build_config(self, raw: Dict[str, Any]) -> VITConfig:
            _v = self._build_section
            return VITConfig(
                app=_v(AppConfig, raw),
                db=_v(DatabaseConfig, raw),
                redis=_v(RedisConfig, raw),
                ai=_v(AIConfig, raw),
                blockchain=_v(BlockchainConfig, raw),
                external=_v(ExternalServicesConfig, raw),
                tachyon=_v(TachyonConfig, raw),
                feature_flags=feature_flag_manager.get_all_flags(),
            )

        @staticmethod
        def _build_section(model: Type[Any], raw: Dict[str, Any]) -> Any:
            """
            Instantiate one config section from alias-keyed raw data.
            Pydantic v2: model.model_validate(data)  (aliases resolved natively).
            Pydantic v1: model(**data)               (aliases accepted in __init__).
            On error:    model()                     (all-defaults fallback).
            """
            section_data: Dict[str, Any] = {}
            if hasattr(model, "model_fields"):
                # Pydantic v2
                for fname, finfo in model.model_fields.items():
                    alias = finfo.alias or fname
                    if alias in raw:
                        section_data[alias] = raw[alias]
                try:
                    return model.model_validate(section_data)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[config] %s validation failed (%s) — using defaults",
                        model.__name__, exc,
                    )
                    try:
                        return model()
                    except Exception:
                        return model.model_construct()
            else:
                # Pydantic v1
                for fname, field in model.__fields__.items():
                    alias = getattr(field, "alias", None) or fname
                    if alias in raw:
                        section_data[alias] = raw[alias]
                try:
                    return model(**section_data)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[config] %s validation failed (%s) — using defaults",
                        model.__name__, exc,
                    )
                    return model()

        @staticmethod
        def _make_default_config() -> VITConfig:
            """All-defaults VITConfig — safe boot fallback."""
            return VITConfig(
                app=AppConfig(),
                db=DatabaseConfig(),
                redis=RedisConfig(),
                ai=AIConfig(),
                blockchain=BlockchainConfig(),
                external=ExternalServicesConfig(),
                tachyon=TachyonConfig(),
                feature_flags={},
            )

        def _get_missing_required_keys(self) -> list:
            """Return commonly-used keys absent from the environment."""
            return [
                k for k in ("ISPORTS_API_KEY", "PAYSTACK_SECRET_KEY", "RESEND_API_KEY")
                if not os.getenv(k)
            ]


    config_manager = ConfigurationManager()
    