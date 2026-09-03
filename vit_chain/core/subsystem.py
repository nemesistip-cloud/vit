import asyncio
import logging
import time
from typing import Dict, Any, Optional
from app.core.kernel import Subsystem
from app.core.registry.models import ModuleMetadata, HealthStatus
from .manager import BlockchainManager
from .query import BlockchainQueryEngine
from ..genesis import ensure_genesis
from app.db.database import AsyncSessionLocal
from app.core.event_bus import event_bus

logger = logging.getLogger(__name__)

# Retry configuration for startup genesis seeding
_GENESIS_MAX_ATTEMPTS = 3
_GENESIS_BACKOFF_SECONDS = (1, 2, 4)  # Per attempt


class BlockchainSubsystem(Subsystem):
    """
    Authoritative Kernel Subsystem for the VIT Blockchain Runtime.
    Handles lifecycle, genesis, and coordination with other core systems.
    """
    name = "blockchain"
    dependencies = ["config", "observability", "persistence", "database"]

    def __init__(self, kernel):
        super().__init__(kernel)
        self.manager = None
        self.query_engine = None
        self._sdk = None
        self._metadata = ModuleMetadata(
            module_id=self.name,
            name="Blockchain Runtime",
            owner="core",
            domain="infrastructure",
            version="1.0.0",
            capabilities=[
                "LedgerProvider",
                "TransactionExecution",
                "MempoolService",
                "ChainVerification",
                "BlockchainSDK"
            ],
            dependencies=self.dependencies
        )

    async def _on_initialize(self, config: Dict[str, Any]):
        """Initialize the blockchain manager and mempool configuration."""
        logger.info("[blockchain] Initializing VIT Blockchain Runtime...")

        bc_config = config.get("blockchain", {})
        mempool_size = bc_config.get("mempool_max_size", 5000)
        tx_ttl = bc_config.get("transaction_ttl", 3600)

        self.manager = BlockchainManager(mempool_size=mempool_size, tx_ttl=tx_ttl)
        self.query_engine = BlockchainQueryEngine()

        # Lazy load SDK to avoid circular imports if any
        from app.modules.blockchain.sdk import BlockchainSDK
        self._sdk = BlockchainSDK(self)

        logger.info(f"[blockchain] Manager initialized (mempool: {mempool_size}, ttl: {tx_ttl}s)")

    async def _on_start(self):
        """Ensure genesis block and start synchronization services.

        Retries ensure_genesis up to _GENESIS_MAX_ATTEMPTS times with
        exponential backoff before raising and marking the subsystem UNHEALTHY.
        """
        from app.core.observability.manager import obs_manager
        from app.core.observability.models import HealthStatus as ObsHealthStatus

        logger.info("[blockchain] Starting VIT Blockchain Subsystem...")

        last_exc: Optional[Exception] = None
        for attempt in range(1, _GENESIS_MAX_ATTEMPTS + 1):
            try:
                async with AsyncSessionLocal() as session:
                    # 1. Ensure genesis block exists
                    genesis_block = await ensure_genesis(session)
                    logger.info(
                        f"[blockchain] Genesis verified (hash: {genesis_block.block_hash[:16]}...) "
                        f"on attempt {attempt}"
                    )

                    # 2. Verify ledger integrity
                    is_valid = await self.manager.verify_chain_integrity(session)
                    if not is_valid:
                        logger.error("[blockchain] LEDGER CORRUPTION DETECTED during startup!")
                        self.error_count += 1
                    else:
                        logger.info("[blockchain] Ledger integrity verified.")

                    await session.commit()

                # Genesis succeeded — break out of retry loop
                break

            except Exception as exc:
                last_exc = exc
                logger.error(
                    "[blockchain] Attempt %d/%d failed: %s",
                    attempt, _GENESIS_MAX_ATTEMPTS, exc,
                    exc_info=True,
                )
                if attempt < _GENESIS_MAX_ATTEMPTS:
                    backoff = _GENESIS_BACKOFF_SECONDS[attempt - 1]
                    logger.info("[blockchain] Retrying in %ds...", backoff)
                    await asyncio.sleep(backoff)
        else:
            # All attempts exhausted — mark UNHEALTHY explicitly so obs_manager
            # reflects real state and kernel rolls up to DEGRADED correctly.
            obs_manager.health.update_status(
                "blockchain",
                ObsHealthStatus.UNHEALTHY,
                f"Genesis seeding failed after {_GENESIS_MAX_ATTEMPTS} attempts: {last_exc}",
            )
            logger.error(
                "[blockchain] Subsystem startup FAILED after %d attempts. Last error: %s",
                _GENESIS_MAX_ATTEMPTS, last_exc,
            )
            raise RuntimeError(
                f"BlockchainSubsystem: genesis failed after {_GENESIS_MAX_ATTEMPTS} attempts"
            ) from last_exc

        await event_bus.publish("ChainInitialized", {"height": 0}, sender="blockchain_subsystem")
        logger.info("[blockchain] Subsystem active.")

    def get_sdk(self):
        """Returns the public SDK for this subsystem."""
        return self._sdk

    async def health_check(self) -> bool:
        """Check the health of the blockchain manager and ledger."""
        if not self.manager:
            return False

        try:
            async with AsyncSessionLocal() as session:
                latest = await self.manager.get_latest_block(session)
            return latest is not None
        except Exception as exc:
            logger.error("[blockchain] health_check exception: %s", exc)
            return False

    async def get_diagnostics(self) -> Dict[str, Any]:
        """Return runtime diagnostics for the blockchain platform."""
        diags = await super().get_diagnostics()
        mempool_stats = await self.manager.get_mempool_stats()

        chain_stats = {}
        try:
            async with AsyncSessionLocal() as session:
                chain_stats = await self.manager.indexer.get_chain_stats(session)
        except Exception as e:
            logger.warning(f"Failed to fetch chain stats for diagnostics: {e}")

        diags.update({
            "mempool": mempool_stats,
            "chain": chain_stats,
            "version": self._metadata.version,
            "domain": self._metadata.domain
        })
        return diags
