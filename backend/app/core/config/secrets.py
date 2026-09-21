import os
import logging
from typing import List, Dict, Any, Optional
from pydantic import SecretStr

logger = logging.getLogger(__name__)

class SecretsManager:
    """Manages secure resolution and redaction of sensitive configuration."""

    def __init__(self):
        self._secrets: Dict[str, SecretStr] = {}

    async def resolve_secrets(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve secrets from external providers (e.g., GCP Secret Manager).
        Updates os.environ for backward compatibility.
        """
        project_id = config_data.get("GCP_PROJECT_ID") or os.getenv("GCP_PROJECT_ID")
        if not project_id:
            return config_data

        try:
            from app.services.gcp_secrets import gcp_secrets
            # List of secret keys to attempt loading
            secret_keys = [
                "PAYSTACK_SECRET_KEY",
                "PAYSTACK_WEBHOOK_SECRET",
                "JWT_SECRET_KEY",
                "SECRET_KEY",
                "DATABASE_URL",
                "REDIS_URL",
                "FOOTBALL_DATA_API_KEY",
                "ODDS_API_KEY",
                "ISPORTS_API_KEY",
                "TELEGRAM_BOT_TOKEN",
                "RESEND_API_KEY",
                "VIT_VALIDATOR_KEY",
                "VIT_TREASURY_PRIVATE_KEY",
                "TACHYON_ENCRYPTION_KEY",
            ]

            # Load secrets into environment for now (to support legacy config)
            await gcp_secrets.load_secrets_to_env(secret_keys)

            # Update config_data with newly loaded environment variables
            for key in secret_keys:
                if val := os.getenv(key):
                    config_data[key] = val

        except ImportError:
            logger.warning("[secrets] GCP Secrets module not available.")
        except Exception as e:
            logger.error(f"[secrets] Failed to resolve secrets: {e}")

        return config_data

    def redact(self, data: Any) -> Any:
        """Recursively redact SecretStr values in a dictionary or model."""
        if isinstance(data, dict):
            return {k: self.redact(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.redact(v) for v in data]
        elif isinstance(data, SecretStr):
            return "********"
        elif hasattr(data, "dict"): # Pydantic model
            return self.redact(data.dict())
        return data

secrets_manager = SecretsManager()
