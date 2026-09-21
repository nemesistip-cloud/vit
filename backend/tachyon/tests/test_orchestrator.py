import pytest
import asyncio
import hashlib
from unittest.mock import MagicMock, AsyncMock, patch
from tachyon.core.orchestrator import TachyonOrchestrator
from app.core.errors import AppError

@pytest.mark.asyncio
async def test_orchestrator_upload_size_validation():
    orch = TachyonOrchestrator()
    data = b"a" * (101 * 1024 * 1024) # 101 MB
    db = AsyncMock()

    with pytest.raises(AppError) as exc:
        await orch.upload(db, "test_file", "test.txt", data)
    assert exc.value.code == "file_too_large"

@pytest.mark.asyncio
async def test_orchestrator_upload_success():
    orch = TachyonOrchestrator()

    # Directly mock the pool instance on the orch
    orch.pool.upload_shard = AsyncMock(return_value=("mock_provider", "mock_file_id"))
    orch.manifests.create = AsyncMock(return_value=MagicMock())
    orch.codec.encode = MagicMock(return_value=[b"shard"] * 9)
    orch.codec.shard_hash = MagicMock(return_value="hash")

    db = AsyncMock()
    # Mock result and scalar_one_or_none
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    data = b"Hello world"
    manifest = await orch.upload(db, "test_file", "test.txt", data)

    assert orch.pool.upload_shard.call_count == 9
    assert orch.manifests.create.called

@pytest.mark.asyncio
async def test_orchestrator_retrieve_success():
    orch = TachyonOrchestrator()

    # Mock manifest
    mock_manifest = MagicMock()
    mock_manifest.provider_mapping = {
        "shards": [
            {"shard_index": i, "provider_id": "p1", "file_id": f"f{i}", "shard_hash": "hash"}
            for i in range(9)
        ],
        "_metadata": {"sha256": "64ec88ca00b268e5ba1a35678a1b5316d212f4f366b2477232534a8aeca37f3c"} # SHA256 of b"Hello world"
    }
    orch.manifests.get = AsyncMock(return_value=mock_manifest)

    # Mock codec decode
    orch.codec.decode = MagicMock(return_value=b"Hello world")

    # Mock retriever
    orch.retriever.retrieve_shards_parallel = AsyncMock(return_value=[b"shard"] * 9)

    db = AsyncMock()
    data = await orch.retrieve(db, "test_file")

    assert data == b"Hello world"
    assert orch.retriever.retrieve_shards_parallel.called

@pytest.mark.asyncio
async def test_orchestrator_verify():
    orch = TachyonOrchestrator()

    mock_manifest = MagicMock()
    mock_manifest.provider_mapping = {
        "shards": [
            {"shard_index": i, "provider_id": "p1", "file_id": f"f{i}", "shard_hash": "hash"}
            for i in range(9)
        ]
    }
    orch.manifests.get = AsyncMock(return_value=mock_manifest)
    orch.retriever.retrieve_shards_parallel = AsyncMock(return_value=[b"data"] * 3)
    orch.codec.shard_hash = MagicMock(return_value="hash")
    orch.manifests.update_health = AsyncMock()

    db = AsyncMock()
    result = await orch.verify(db, "test_file")

    assert result["verified"] is True
    assert result["shards_checked"] == 3
    assert result["shards_healthy"] == 3
    assert orch.manifests.update_health.called
