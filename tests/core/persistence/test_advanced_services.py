import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.core.persistence.cache import CacheManager
from app.core.persistence.audit import AuditRepository, AuditLog
from app.core.persistence.backup import BackupManager, RecoveryManager
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_cache_manager():
    redis_mock = AsyncMock()
    redis_mock.get.return_value = '{"foo": "bar"}'

    cache = CacheManager(redis_mock)
    val = await cache.get("test_key")

    assert val == {"foo": "bar"}
    redis_mock.get.assert_called_once_with("test_key")

    await cache.set("new_key", {"baz": 1})
    redis_mock.set.assert_called_once()

@pytest.mark.asyncio
async def test_audit_repository():
    session_mock = AsyncMock(spec=AsyncSession)
    repo = AuditRepository(session_mock)

    await repo.log_change(
        module="core",
        entity="user",
        entity_id=1,
        action="UPDATE",
        previous={"name": "old"},
        new={"name": "new"}
    )

    session_mock.add.assert_called_once()
    session_mock.flush.assert_called_once()

@pytest.mark.asyncio
async def test_backup_manager():
    mgr = BackupManager({})
    filename = await mgr.create_backup("test")
    assert "test" in filename
    assert filename.endswith(".sql")

    verified = await mgr.verify_backup(filename)
    assert verified is True

@pytest.mark.asyncio
async def test_recovery_manager():
    backup_mock = AsyncMock(spec=BackupManager)
    backup_mock.verify_backup.return_value = True

    recovery = RecoveryManager(backup_mock)
    success = await recovery.restore_backup("some_file.sql")

    assert success is True
    backup_mock.verify_backup.assert_called_once_with("some_file.sql")
