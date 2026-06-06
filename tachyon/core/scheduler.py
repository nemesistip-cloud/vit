import asyncio
from typing import List, Dict, Any, Optional
import logging
from tachyon.core.shredder import TachyonShredder

class TachyonScheduler:
    """
    Manages the Tachyon Burst Transfer Protocol (TBTP).
    Coordinates parallel requests across multiple cloud provider accounts.
    """

    def __init__(self, providers: List[Any]):
        self.providers = providers
        self.shredder = TachyonShredder()

    async def upload_burst(self, data: bytes, file_id: str) -> List[Any]:
        """
        Burst upload: Shreds file and dispatches fragments in parallel.
        """
        if not self.providers:
            raise ValueError("No providers configured")

        fragments, parities = self.shredder.encode(data)
        all_fragments = fragments + parities

        tasks = []
        for i, frag in enumerate(all_fragments):
            # Round-robin selection of provider for prototype
            provider = self.providers[i % len(self.providers)]
            fragment_name = f"tachyon_{file_id}_{i}"
            tasks.append(provider.upload_fragment(frag, fragment_name))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    async def download_burst(self, fragment_names: List[str], fragment_to_provider_map: Dict[str, int], size_bytes: int) -> bytes:
        """
        Burst download: Fetches fragments in parallel and reassembles with EEC.
        """
        tasks = []
        for name in fragment_names:
            provider_idx = fragment_to_provider_map.get(name)
            if provider_idx is None:
                continue
            provider = self.providers[provider_idx]
            tasks.append(provider.download_fragment(name))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_fragments = []
        for res in results:
            if isinstance(res, Exception):
                processed_fragments.append(None)
            else:
                # Integrity check
                if res and len(res) == 4096:
                    actual_hash = TachyonShredder.get_fragment_hash(res)
                    # In a real system, we would verify against the manifest hash
                    # logging.getLogger(__name__).debug(f"Fragment verified: {actual_hash}")
                processed_fragments.append(res)

        if not processed_fragments:
            return b""

        # In our upgraded burst protocol, the last `parity_shards` fragments are parity
        num_data_shards = (size_bytes + 4095) // 4096
        data_fragments = processed_fragments[:num_data_shards]
        parity_fragments = processed_fragments[num_data_shards:]

        # Ensure parity_fragments is not empty for XOR fallback
        if not parity_fragments and num_data_shards < len(processed_fragments):
             parity_fragments = [processed_fragments[num_data_shards]]

        return self.shredder.decode(data_fragments, parity_fragments, size_bytes)

if __name__ == "__main__":
    # Mock Provider for testing
    class MockProvider:
        def __init__(self, name):
            self.name = name
            self.storage = {}
        async def upload_fragment(self, data, name):
            print(f"[{self.name}] Uploading {name}...")
            self.storage[name] = data
            await asyncio.sleep(0.1)
            return True
        async def download_fragment(self, name):
            print(f"[{self.name}] Downloading {name}...")
            await asyncio.sleep(0.1)
            return self.storage[name]

    async def test():
        p1 = MockProvider("G-Drive-1")
        p2 = MockProvider("OneDrive-1")
        scheduler = TachyonScheduler([p1, p2])

        test_data = b"Tachyon Parallel Burst Test" * 100
        print("Starting Burst Upload...")
        await scheduler.upload_burst(test_data, "test_file_001")

        print("\nStarting Burst Download (Standard)...")
        # 1 data shard + 2 parity shards = 3 total
        fragment_names = [f"tachyon_test_file_001_{i}" for i in range(3)]
        mapping = {name: i % 2 for i, name in enumerate(fragment_names)}
        recovered = await scheduler.download_burst(fragment_names, mapping, len(test_data))

        print(f"\nRecovered data length: {len(recovered)}")
        assert recovered == test_data
        print("Standard download verified.")

        print("\nStarting Burst Download (with 2 missing fragments - EEC test)...")
        # Simulate missing fragments by removing them from providers
        # We have 2 parity shards, so we can lose up to 2 fragments total
        del p1.storage["tachyon_test_file_001_0"] # Data shard
        del p2.storage["tachyon_test_file_001_1"] # Parity shard 1

        recovered_eec = await scheduler.download_burst(fragment_names, mapping, len(test_data))
        print(f"Recovered (EEC) data length: {len(recovered_eec)}")
        assert recovered_eec == test_data
        print("EEC (RS) multi-fragment recovery verified.")

    asyncio.run(test())
