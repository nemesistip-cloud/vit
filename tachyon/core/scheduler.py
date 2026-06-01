import asyncio
from typing import List, Dict, Any, Optional
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

        fragments, parity = self.shredder.encode(data)
        all_fragments = fragments + [parity]

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
                processed_fragments.append(res)

        if not processed_fragments:
            return b""

        # In our burst protocol, the last fragment is parity
        data_fragments = processed_fragments[:-1]
        parity_fragment = processed_fragments[-1]

        return self.shredder.decode(data_fragments, parity_fragment, size_bytes)

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
        fragment_names = ["tachyon_test_file_001_0", "tachyon_test_file_001_1"]
        mapping = {name: i % 2 for i, name in enumerate(fragment_names)}
        recovered = await scheduler.download_burst(fragment_names, mapping, len(test_data))

        print(f"\nRecovered data length: {len(recovered)}")
        assert recovered == test_data
        print("Standard download verified.")

        print("\nStarting Burst Download (with 1 missing fragment - EEC test)...")
        # Simulate missing fragment by removing it from provider
        del p1.storage["tachyon_test_file_001_0"]

        recovered_eec = await scheduler.download_burst(fragment_names, mapping, len(test_data))
        print(f"Recovered (EEC) data length: {len(recovered_eec)}")
        assert recovered_eec == test_data
        print("EEC recovery verified.")

    asyncio.run(test())
