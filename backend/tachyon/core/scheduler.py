import asyncio
from typing import List, Dict, Any, Optional
import logging
from tachyon.core.shredder import TachyonShredder

_UPLOAD_SEM = asyncio.Semaphore(2)   # reduced from 4 to limit memory pressure
_DOWNLOAD_SEM = asyncio.Semaphore(4)

# Circuit-breaker: if this fraction of tasks fail in the first probe, abort early
_CIRCUIT_THRESHOLD = 0.8            # >80% fail → stop the burst
_PROBE_SIZE = 4                     # probe this many tasks first

logger = logging.getLogger(__name__)


class TachyonScheduler:
    """
    Manages the Tachyon Burst Transfer Protocol (TBTP).
    Coordinates parallel requests across multiple cloud provider accounts.
    Semaphore-limited to avoid concurrent SSL exhaustion / segfaults.
    Circuit-breaker aborts early when all providers are consistently failing.
    """

    def __init__(self, providers: List[Any]):
        self.providers = providers
        self.shredder = TachyonShredder()

    async def upload_burst(self, data: bytes, file_id: str) -> List[Any]:
        """
        Burst upload: Shreds file and dispatches fragments with bounded concurrency.
        Uses a circuit-breaker to abort early when providers are failing.
        """
        if not self.providers:
            raise ValueError("No providers configured")

        fragments, parities = self.shredder.encode(data)
        all_fragments = fragments + parities

        async def _upload_one(frag: bytes, fragment_name: str, provider: Any) -> Any:
            async with _UPLOAD_SEM:
                try:
                    result = await asyncio.wait_for(
                        provider.upload_fragment(frag, fragment_name),
                        timeout=8.0  # hard per-task timeout — prevents native-code hangs
                    )
                    return result
                except asyncio.TimeoutError:
                    logger.warning("[tachyon] upload %s timed out", fragment_name)
                    return TimeoutError(fragment_name)
                except Exception as e:
                    logger.error("[tachyon] upload %s failed: %s", fragment_name, e)
                    return e

        # ── Circuit-breaker probe ─────────────────────────────────────────────
        # Test the first _PROBE_SIZE tasks; if nearly all fail, skip the rest.
        probe_count = min(_PROBE_SIZE, len(all_fragments))
        probe_tasks = []
        for i in range(probe_count):
            provider = self.providers[i % len(self.providers)]
            fragment_name = f"tachyon_{file_id}_{i}"
            probe_tasks.append(_upload_one(all_fragments[i], fragment_name, provider))

        probe_results = await asyncio.gather(*probe_tasks, return_exceptions=True)
        failures = sum(1 for r in probe_results if isinstance(r, (Exception, BaseException)))
        fail_rate = failures / max(probe_count, 1)

        if fail_rate >= _CIRCUIT_THRESHOLD and len(all_fragments) > probe_count:
            logger.warning(
                "[tachyon] circuit-breaker: %d/%d probe tasks failed (%.0f%%) — "
                "aborting burst upload of %d remaining fragments",
                failures, probe_count, fail_rate * 100, len(all_fragments) - probe_count,
            )
            # Return probe results + None placeholders for skipped fragments
            return list(probe_results) + [None] * (len(all_fragments) - probe_count)

        # ── Full burst (probes passed) ────────────────────────────────────────
        remaining_tasks = []
        for i in range(probe_count, len(all_fragments)):
            provider = self.providers[i % len(self.providers)]
            fragment_name = f"tachyon_{file_id}_{i}"
            remaining_tasks.append(_upload_one(all_fragments[i], fragment_name, provider))

        remaining_results = await asyncio.gather(*remaining_tasks, return_exceptions=True)
        return list(probe_results) + list(remaining_results)

    async def download_burst(self, fragment_names: List[str], fragment_to_provider_map: Dict[str, int], size_bytes: int) -> bytes:
        """
        Burst download: Fetches fragments with bounded concurrency and reassembles with EEC.
        """
        async def _download_one(name: str, provider: Any) -> Any:
            async with _DOWNLOAD_SEM:
                try:
                    return await asyncio.wait_for(
                        provider.download_fragment(name),
                        timeout=15.0
                    )
                except Exception as e:
                    logger.error("[tachyon] download %s failed: %s", name, e)
                    return None

        tasks = []
        for name in fragment_names:
            provider_idx = fragment_to_provider_map.get(name)
            if provider_idx is None:
                continue
            provider = self.providers[provider_idx]
            tasks.append(_download_one(name, provider))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        data_shards = []
        parity_shards = []

        num_data = (size_bytes + 4095) // 4096

        for i, res in enumerate(results):
            fragment_data = None
            if not isinstance(res, Exception) and res is not None:
                if len(res) == 4096:
                    TachyonShredder.get_fragment_hash(res)
                fragment_data = res

            if i < num_data:
                data_shards.append(fragment_data)
            else:
                parity_shards.append(fragment_data)

        decoded = self.shredder.decode(data_shards, parity_shards, size_bytes)
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
                    return await asyncio.wait_for(
                        provider.upload_fragment(frag, fragment_name),
                        timeout=8.0
                    )
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
                    await asyncio.wait_for(
                        provider.upload_fragment(all_fragments[idx], fragment_name),
                        timeout=8.0
                    )
                    logger.info("[tachyon] repaired fragment %s", fragment_name)
                except Exception as e:
                    logger.error("[tachyon] repair failed for %s: %s", fragment_name, e)
