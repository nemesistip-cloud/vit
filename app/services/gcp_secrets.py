"""app/services/gcp_secrets.py — GCP Secret Manager client with graceful fallback.

``GCP_SECRETS_AVAILABLE`` is ``False`` when google-cloud-secret-manager is
not installed; ``load_secrets_to_env`` becomes a safe no-op.
"""
from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)

try:
    from google.cloud import secretmanager as _secretmanager
    GCP_SECRETS_AVAILABLE = True
except ImportError:
    _secretmanager = None   # type: ignore[assignment]
    GCP_SECRETS_AVAILABLE = False
    logger.debug(
        "google-cloud-secret-manager not installed — GCP secret loading disabled. "
        "Install with: pip install google-cloud-secret-manager"
    )


class GCPSecretsClient:
    """Loads GCP secrets into process environment variables at startup."""

    def __init__(self) -> None:
        self.project_id: str | None = os.getenv("GCP_PROJECT_ID")

    async def load_secrets_to_env(self, names: list[str]) -> int:
        """Fetch each named secret and inject it into ``os.environ``.

        Returns the number of secrets successfully loaded.
        Silently skips entries it cannot reach rather than crashing.
        """
        if not GCP_SECRETS_AVAILABLE:
            logger.debug("GCP secret loading skipped — library not installed")
            return 0
        if not self.project_id:
            logger.debug("GCP secret loading skipped — GCP_PROJECT_ID not set")
            return 0

        client = _secretmanager.SecretManagerServiceClient()  # type: ignore[union-attr]
        count  = 0
        for name in names:
            try:
                res = client.access_secret_version(
                    request={
                        "name": f"projects/{self.project_id}/secrets/{name}/versions/latest"
                    }
                )
                os.environ[name] = res.payload.data.decode("UTF-8")
                count += 1
            except Exception as exc:
                logger.warning("Failed to load GCP secret '%s': %s", name, exc)
        return count


gcp_secrets = GCPSecretsClient()
