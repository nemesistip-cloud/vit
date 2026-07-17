import sys
import os

path = 'tachyon/core/scheduler.py'
with open(path, 'r') as f:
    content = f.read()

# Add logging import if not there
if 'import logging' not in content:
    content = 'import logging\n' + content

# Modify download_burst to include Lazy Repair
search_text = """        # Ensure parity_fragments is not empty for XOR fallback
        if not parity_fragments and num_data_shards < len(processed_fragments):
             parity_fragments = [processed_fragments[num_data_shards]]

        return self.shredder.decode(data_fragments, parity_fragments, size_bytes)"""

replace_text = """        # Ensure parity_fragments is not empty for XOR fallback
        if not parity_fragments and num_data_shards < len(processed_fragments):
             parity_fragments = [processed_fragments[num_data_shards]]

        try:
            data = self.shredder.decode(data_fragments, parity_fragments, size_bytes)

            # VESS Core: Lazy Repair - restore redundancy if shards were missing
            erased_indices = [i for i, f in enumerate(processed_fragments) if f is None]
            if erased_indices and data:
                logging.getLogger(__name__).info("[tachyon] Lazy Repair triggered for %d shards", len(erased_indices))
                # Trigger repair in background to not block the download response
                asyncio.create_task(self._lazy_repair(data, fragment_names, erased_indices, fragment_to_provider_map))

            return data
        except Exception as e:
            logging.getLogger(__name__).error("[tachyon] download reconstruction failed: %s", e)
            raise

    async def _lazy_repair(self, data: bytes, fragment_names: List[str], erased_indices: List[int], mapping: Dict[str, int]):
        \"\"\"Re-shreds data and re-uploads missing shards to restore swarm health.\"\"\"
        try:
            frags, parities = self.shredder.encode(data)
            all_generated = frags + parities

            tasks = []
            for idx in erased_indices:
                if idx < len(all_generated) and idx < len(fragment_names):
                    name = fragment_names[idx]
                    p_idx = mapping.get(name)
                    if p_idx is not None and p_idx < len(self.providers):
                        provider = self.providers[p_idx]
                        tasks.append(provider.upload_fragment(all_generated[idx], name))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                logging.getLogger(__name__).info("[tachyon] Lazy Repair completed: %d shards restored", sum(1 for r in results if r is True))
        except Exception as e:
            logging.getLogger(__name__).error("[tachyon] Lazy Repair failed: %s", e)"""

if search_text in content:
    content = content.replace(search_text, replace_text)
    with open(path, 'w') as f:
        f.write(content)
    print("Patch applied successfully")
else:
    print("Search text not found")
