import asyncio
import logging
from typing import List, Optional, Dict, Any
from tachyon.core.providers.pool import ProviderPool

logger = logging.getLogger(__name__)

class ShardRetriever:
    async def retrieve_shards_parallel(self,
                                        shard_locations: List[Dict[str, Any]],
                                        pool: ProviderPool) -> List[Optional[bytes]]:
        """
        Download all shards in parallel.
        Map exceptions to None (missing shard).
        Returns list preserving shard_index order.
        """
        # Sort shard_locations by shard_index to ensure output order
        sorted_locations = sorted(shard_locations, key=lambda x: x["shard_index"])

        async def _download(loc):
            try:
                return await pool.download_shard(loc["provider_id"], loc["file_id"])
            except Exception as e:
                logger.error(f"Failed to download shard {loc['shard_index']} from {loc['provider_id']}: {e}")
                return None

        tasks = [_download(loc) for loc in sorted_locations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Ensure exceptions are mapped to None
        final_results = []
        for i, res in enumerate(results):
            if isinstance(res, Exception) or res is None:
                final_results.append(None)
            else:
                final_results.append(res)

        return final_results
