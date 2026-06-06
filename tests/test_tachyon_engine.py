import pytest
import asyncio
from unittest.mock import MagicMock, patch
from tachyon.core.shredder import TachyonShredder, CHUNK_SIZE
from tachyon.core.scheduler import TachyonScheduler

@pytest.mark.asyncio
async def test_shredder_rs_flow():
    """Test full RS shredding and reconstruction."""
    shredder = TachyonShredder(parity_shards=2)
    # Ensure RS is available for this test if possible, else skip or expect XOR

    test_data = b"Tachyon RS Engine Test Data " * 100
    original_size = len(test_data)

    # Encode
    fragments, parities = shredder.encode(test_data)

    # Simulate loss of two fragments (one data, one parity)
    data_with_loss = list(fragments)
    data_with_loss[0] = None

    parity_with_loss = list(parities)
    parity_with_loss[0] = None

    # Decode
    recovered = shredder.decode(data_with_loss, parity_with_loss, original_size)
    assert recovered == test_data

@pytest.mark.asyncio
async def test_shredder_xor_fallback():
    """Test XOR fallback when RS is missing."""
    shredder = TachyonShredder(parity_shards=1)

    # Force XOR fallback by mocking rs to None
    with patch.object(shredder, "rs", None):
        test_data = b"Tachyon XOR Fallback Test Data " * 50
        original_size = len(test_data)

        fragments, parities = shredder.encode(test_data)
        assert len(parities) == 1

        # Simulate loss of one data fragment
        data_with_loss = list(fragments)
        data_with_loss[0] = None

        # Decode
        recovered = shredder.decode(data_with_loss, parities, original_size)
        assert recovered == test_data

@pytest.mark.asyncio
async def test_scheduler_burst_logic():
    """Test TachyonScheduler parallel burst operations."""
    class MockProvider:
        def __init__(self, name):
            self.name = name
            self.storage = {}
        async def upload_fragment(self, data, name):
            self.storage[name] = data
            return True
        async def download_fragment(self, name):
            return self.storage.get(name)

    p1 = MockProvider("P1")
    p2 = MockProvider("P2")
    scheduler = TachyonScheduler([p1, p2])

    test_data = b"Burst Parallel Test " * 20
    file_id = "test_burst_001"

    # Upload
    await scheduler.upload_burst(test_data, file_id)

    # Verify fragments distributed
    assert len(p1.storage) + len(p2.storage) > 0

    # Reconstruct manifest-like info
    num_fragments = (len(test_data) + CHUNK_SIZE - 1) // CHUNK_SIZE + scheduler.shredder.parity_shards
    fragment_names = [f"tachyon_{file_id}_{i}" for i in range(num_fragments)]
    mapping = {name: i % 2 for i, name in enumerate(fragment_names)}

    # Download
    recovered = await scheduler.download_burst(fragment_names, mapping, len(test_data))
    assert recovered == test_data

    # Test recovery from loss in scheduler
    p1.storage.clear() # Lose half the fragments
    recovered_with_loss = await scheduler.download_burst(fragment_names, mapping, len(test_data))
    # Note: If parity is 2 and we lose too many, it might fail.
    # But here we lost p1 which might contain more than 2 shards if file is large.
    # For this small test data, 1 shard + 2 parity = 3 total.
    # mapping: {0:0, 1:1, 2:0}. p1 has index 0. p1.storage has {frag0, frag2}.
    # If we clear p1, we lose frag0 and frag2. Only frag1 (parity) remains.
    # 2 shards lost, 2 parity available. It should recover!
    assert recovered_with_loss == test_data
