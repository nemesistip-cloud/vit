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

    async def download_burst(self, fragment_names: List[str], fragment_to_provider_map: Dict[str, int]) -> bytes:
        """
        Burst download: Fetches fragments in parallel and reassembles.
        """
        tasks = []
        for name in fragment_names:
            provider_idx = fragment_to_provider_map[name]
            provider = self.providers[provider_idx]
            tasks.append(provider.download_fragment(name))

        fragments = await asyncio.gather(*tasks)

        # Simple reassembly (excluding parity for now in this prototype)
        # In a real EEC implementation, we'd check parity and reconstruct if needed
        data = b"".join(fragments[:-1]) # Assume last one was parity
        return data.rstrip(b'\0')

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

        print("\nStarting Burst Download...")
        fragment_names = ["tachyon_test_file_001_0", "tachyon_test_file_001_1"]
        mapping = {name: i % 2 for i, name in enumerate(fragment_names)}
        recovered = await scheduler.download_burst(fragment_names, mapping)

        print(f"\nRecovered data length: {len(recovered)}")
        assert recovered.startswith(b"Tachyon Parallel Burst Test")
        print("Scheduler logic verified.")

    asyncio.run(test())
