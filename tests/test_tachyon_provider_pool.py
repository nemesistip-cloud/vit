import pytest
import os
import shutil
from tachyon.core.providers.pool import ProviderPool
from tachyon.core.providers.disk import LocalDiskProvider
from app.core.errors import AppError

@pytest.mark.asyncio
async def test_provider_pool_local_fallback_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("GDRIVE_SERVICE_ACCOUNT_KEYS", "[]")
    monkeypatch.setenv("ONEDRIVE_ACCOUNTS", "[]")
    monkeypatch.setenv("DROPBOX_TOKENS", "[]")
    monkeypatch.setenv("TACHYON_ALLOW_LOCAL_STORAGE", "true")

    pool = ProviderPool()
    assert len(pool.providers) == 1
    assert isinstance(pool.providers[0], LocalDiskProvider)

    # Test upload and download
    shard_id = "test_shard_1"
    test_data = b"hello tachyon pool"

    pid, file_id = await pool.upload_shard(shard_id, test_data)
    assert pid == "local_disk_0"
    assert file_id == shard_id

    downloaded = await pool.download_shard(pid, file_id)
    assert downloaded == test_data

    # Test delete
    deleted = await pool.delete_shard(pid, file_id)
    assert deleted is True

@pytest.mark.asyncio
async def test_provider_pool_local_fallback_disabled(monkeypatch):
    monkeypatch.setenv("GDRIVE_SERVICE_ACCOUNT_KEYS", "[]")
    monkeypatch.setenv("ONEDRIVE_ACCOUNTS", "[]")
    monkeypatch.setenv("DROPBOX_TOKENS", "[]")
    monkeypatch.setenv("TACHYON_ALLOW_LOCAL_STORAGE", "false")

    pool = ProviderPool()
    assert len(pool.providers) == 0

    # Upload should raise storage_unavailable
    with pytest.raises(AppError) as exc_info:
        await pool.upload_shard("shard_fail", b"data")
    assert exc_info.value.code == "storage_unavailable"

@pytest.mark.asyncio
async def test_local_disk_provider_direct(tmp_path):
    provider = LocalDiskProvider("test_disk_account", storage_path=str(tmp_path))

    health = await provider.health_check()
    assert health is True

    usage = await provider.get_usage()
    assert usage["quota_bytes"] > 0

    f_id = await provider.upload_shard("s1", b"content")
    assert f_id == "s1"

    data = await provider.download_shard("s1")
    assert data == b"content"

    await provider.delete_shard("s1")
    with pytest.raises(FileNotFoundError):
        await provider.download_shard("s1")
