import asyncio
from typing import List, Dict, Any, Optional
import logging
from tachyon.core.shredder import TachyonShredder

_UPLOAD_SEM = asyncio.Semaphore(4)
_DOWNLOAD_SEM = asyncio.Semaphore(6)

class TachyonScheduler:
    """
    Manages the Tachyon Burst Transfer Protocol (TBTP).
    Coordinates parallel requests across multiple cloud provider accounts.
    Semaphore-limited to avoid concurrent SSL exhaustion / segfaults.
    """

    def __init__(self, providers: List[Any]):
        self.providers = providers
        self.shredder = TachyonShredder()

    async def upload_burst(self, data: bytes, file_id: str) -> List[Any]:
        """
        Burst upload: Shreds file and dispatches fragments with bounded concurrency.
        """
        if not self.providers:
            raise ValueError("No providers configured")

        fragments, parities = self.shredder.encode(data)
        all_fragments = fragments + parities

        async def _upload_one(frag: bytes, fragment_name: str, provider: Any) -> Any:
            async with _UPLOAD_SEM:
                try:
                    return await provider.upload_fragment(frag, fragment_name)
                except Exception as e:
                    logging.getLogger(__name__).error(
                        f"[tachyon] upload {fragment_name} failed: {e}"
                    )
                    return e

        tasks = []
        for i, frag in enumerate(all_fragments):
            provider = self.providers[i % len(self.providers)]
            fragment_name = f"tachyon_{file_id}_{i}"
            tasks.append(_upload_one(frag, fragment_name, provider))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    async def download_burst(self, fragment_names: List[str], fragment_to_provider_map: Dict[str, int], size_bytes: int) -> bytes:
        """
        Burst download: Fetches fragments with bounded concurrency and reassembles with EEC.
        """
        async def _download_one(name: str, provider: Any) -> Any:
            async with _DOWNLOAD_SEM:
                try:
                    return await provider.download_fragment(name)
                except Exception as e:
                    logging.getLogger(__name__).error(
                        f"[tachyon] download {name} failed: {e}"
                    )
                    return None

        tasks = []
        for name in fragment_names:
            provider_idx = fragment_to_provider_map.get(name)
            if provider_idx is None:
                continue
            provider = self.providers[provider_idx]
            tasks.append(_download_one(name, provider))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_fragments = []
        for res in results:
            if isinstance(res, Exception) or res is None:
                processed_fragments.append(None)
            else:
                if res and len(res) == 4096:
                    TachyonShredder.get_fragment_hash(res)
                processed_fragments.append(res)

        decoded = self.shredder.decode(processed_fragments, size_bytes)
        if decoded is None:
            raise ValueError("EEC decode failed — too many missing/corrupt fragments")
        return decoded

    async def health_check(self) -> Dict[str, Any]:
        """Check connectivity to all configured providers."""
        results = {}
        for i, provider in enumerate(self.providers):
            try:
                ok = await asyncio.wait_for(provider.health_check(), timeout=5.0)
                results[f"provider_{i}"] = {"status": "ok" if ok else "degraded"}
            except asyncio.TimeoutError:
                results[f"provider_{i}"] = {"status": "timeout"}
            except Exception as e:
                results[f"provider_{i}"] = {"status": "error", "detail": str(e)}
        return results

    async def repair_fragment(
        self,
        data: bytes,
        file_id: str,
        fragment_indices: List[int],
    ) -> List[Any]:
        """Re-upload specific fragments (repair mode)."""
        fragments, parities = self.shredder.encode(data)
        all_fragments = fragments + parities

        async def _repair_one(frag: bytes, fragment_name: str, provider: Any) -> Any:
            async with _UPLOAD_SEM:
                try:
                    return await provider.upload_fragment(frag, fragment_name)
                except Exception as e:
                    return e

        tasks = []
        for idx in fragment_indices:
            if idx >= len(all_fragments):
                continue
            provider = self.providers[idx % len(self.providers)]
            fragment_name = f"tachyon_{file_id}_{idx}"
            tasks.append(_repair_one(all_fragments[idx], fragment_name, provider))

        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _lazy_repair(
        self,
        data: bytes,
        fragment_names: List[str],
        erased_indices: List[int],
        fragment_to_provider_map: Dict[str, int],
    ) -> None:
        """Background repair: re-upload missing fragments after a successful decode."""
        logger = logging.getLogger(__name__)
        for idx in erased_indices:
            if idx >= len(fragment_names):
                continue
            fragment_name = fragment_names[idx]
            provider_idx = fragment_to_provider_map.get(fragment_name)
            if provider_idx is None:
                continue
            provider = self.providers[provider_idx]
            fragments, parities = self.shredder.encode(data)
            all_fragments = fragments + parities
            if idx >= len(all_fragments):
                continue
            async with _UPLOAD_SEM:
                try:
                    await provider.upload_fragment(all_fragments[idx], fragment_name)
                    logger.info(f"[tachyon] repaired fragment {fragment_name}")
                except Exception as e:
                    logger.error(f"[tachyon] repair failed for {fragment_name}: {e}")
