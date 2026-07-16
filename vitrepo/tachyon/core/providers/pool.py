import json
import logging
import os
import time
from typing import List, Dict, Any, Tuple, Optional
from app.config import get_env
from app.core.errors import AppError
from tachyon.core.providers.gdrive import GoogleDriveProvider
from tachyon.core.providers.onedrive import OneDriveProvider
from tachyon.core.providers.dropbox import DropboxProvider

logger = logging.getLogger(__name__)

class ProviderPool:
    QUOTA_GUARD_PCT = 0.90
    DEGRADED_TIMEOUT_SECONDS = 600

    def __init__(self):
        self.providers = []
        self.degraded_until = {} # provider_id -> timestamp
        self.usage_cache = {}    # provider_id -> {used_bytes, quota_bytes, available_bytes, timestamp}
        self._current_index = 0
        self._load_providers()

    def _load_providers(self):
        # 1. GDRIVE_SERVICE_ACCOUNT_KEYS (JSON array of SA dicts)
        gdrive_keys_raw = get_env("GDRIVE_SERVICE_ACCOUNT_KEYS", "[]")
        try:
            gdrive_keys = json.loads(gdrive_keys_raw)
            for i, key in enumerate(gdrive_keys):
                self.providers.append(GoogleDriveProvider(f"gdrive_sa_{i}", key))
        except Exception as e:
            logger.error(f"Failed to load GDRIVE_SERVICE_ACCOUNT_KEYS: {e}")

        # 2. GDRIVE_CREDENTIALS_DIR (directory of *.json SA files)
        gdrive_dir = get_env("GDRIVE_CREDENTIALS_DIR", "")
        if gdrive_dir and os.path.isdir(gdrive_dir):
            for filename in os.listdir(gdrive_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(gdrive_dir, filename)
                    try:
                        with open(filepath, "r") as f:
                            key = json.load(f)
                            self.providers.append(GoogleDriveProvider(f"gdrive_file_{filename}", key))
                    except Exception as e:
                        logger.error(f"Failed to load gdrive credential from {filename}: {e}")

        # 3. ONEDRIVE_ACCOUNTS (JSON array of {tenant,client,secret})
        onedrive_accounts_raw = get_env("ONEDRIVE_ACCOUNTS", "[]")
        try:
            onedrive_accounts = json.loads(onedrive_accounts_raw)
            for i, acc in enumerate(onedrive_accounts):
                self.providers.append(OneDriveProvider(f"onedrive_{i}", acc))
        except Exception as e:
            logger.error(f"Failed to load ONEDRIVE_ACCOUNTS: {e}")

        # 4. DROPBOX_TOKENS (JSON array of access tokens)
        dropbox_tokens_raw = get_env("DROPBOX_TOKENS", "[]")
        try:
            dropbox_tokens = json.loads(dropbox_tokens_raw)
            for i, token in enumerate(dropbox_tokens):
                self.providers.append(DropboxProvider(f"dropbox_{i}", {"access_token": token}))
        except Exception as e:
            logger.error(f"Failed to load DROPBOX_TOKENS: {e}")

        logger.info(f"Loaded {len(self.providers)} providers into the pool.")
        if not self.providers:
            logger.critical("No providers loaded in ProviderPool!")

    def _is_degraded(self, provider_id: str) -> bool:
        until = self.degraded_until.get(provider_id, 0)
        return time.time() < until

    async def _is_full(self, provider: Any) -> bool:
        pid = provider.account_id
        now = time.time()

        # Cache usage for 5 minutes
        if pid in self.usage_cache and now - self.usage_cache[pid]["timestamp"] < 300:
            usage = self.usage_cache[pid]
        else:
            usage = await provider.get_usage()
            usage["timestamp"] = now
            self.usage_cache[pid] = usage

        if usage["quota_bytes"] > 0:
            pct = usage["used_bytes"] / usage["quota_bytes"]
            return pct > self.QUOTA_GUARD_PCT
        return False

    async def upload_shard(self, shard_id: str, data: bytes) -> Tuple[str, str]:
        start_index = self._current_index
        num_providers = len(self.providers)

        for _ in range(num_providers):
            provider = self.providers[self._current_index]
            self._current_index = (self._current_index + 1) % num_providers

            pid = provider.account_id
            if self._is_degraded(pid):
                continue

            if await self._is_full(provider):
                continue

            try:
                file_id = await provider.upload_shard(shard_id, data)
                return (pid, file_id)
            except Exception as e:
                logger.error(f"Upload failed for provider {pid}: {e}")
                self.degraded_until[pid] = time.time() + self.DEGRADED_TIMEOUT_SECONDS
                continue

        raise AppError("storage_unavailable", status_code=503, code="storage_unavailable")

    async def download_shard(self, provider_id: str, file_id: str) -> bytes:
        for provider in self.providers:
            if provider.account_id == provider_id:
                try:
                    return await provider.download_shard(file_id)
                except Exception as e:
                    logger.error(f"Download failed from provider {provider_id}: {e}")
                    raise AppError("shard_unavailable", status_code=404, code="shard_unavailable")

        raise AppError("provider_not_found", status_code=404, code="provider_not_found")

    async def delete_shard(self, provider_id: str, file_id: str) -> bool:
        for provider in self.providers:
            if provider.account_id == provider_id:
                return await provider.delete_shard(file_id)
        return False

    async def health_check(self) -> Dict[str, Dict[str, Any]]:
        results = {}
        for provider in self.providers:
            pid = provider.account_id
            healthy = await provider.health_check()
            usage = await provider.get_usage()

            usage_pct = 0.0
            if usage["quota_bytes"] > 0:
                usage_pct = usage["used_bytes"] / usage["quota_bytes"]

            results[pid] = {
                "healthy": healthy,
                "usage_pct": usage_pct
            }
        return results

    def available_provider_count(self) -> int:
        count = 0
        now = time.time()
        for provider in self.providers:
            pid = provider.account_id
            if self._is_degraded(pid):
                continue

            # Note: Checking _is_full is async, so we use the cache here if available
            usage = self.usage_cache.get(pid)
            if usage and usage["quota_bytes"] > 0:
                if usage["used_bytes"] / usage["quota_bytes"] > self.QUOTA_GUARD_PCT:
                    continue

            count += 1
        return count
