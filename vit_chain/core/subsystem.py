import logging
from typing import Dict, Any
from app.core.kernel import Subsystem
from app.core.registry.models import ModuleMetadata, HealthStatus
from .manager import BlockchainManager
from ..genesis import ensure_genesis
from app.db.database import AsyncSessionLocal
from app.core.event_bus import event_bus

logger = logging.getLogger(__name__)

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
                "ChainVerification"
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
        logger.info(f"[blockchain] Manager initialized (mempool: {mempool_size}, ttl: {tx_ttl}s)")

    async def _on_start(self):
        """Ensure genesis block and start synchronization services."""
        logger.info("[blockchain] Starting VIT Blockchain Subsystem...")

        async with AsyncSessionLocal() as session:
            try:
                # 1. Ensure genesis block exists
                genesis_block = await ensure_genesis(session)
                logger.info(f"[blockchain] Genesis verified (hash: {genesis_block.block_hash[:16]}...)")

                # 2. Verify ledger integrity
                is_valid = await self.manager.verify_chain_integrity(session)
                if not is_valid:
                    logger.error("[blockchain] LEDGER CORRUPTION DETECTED during startup!")
                    self.error_count += 1
                else:
                    logger.info("[blockchain] Ledger integrity verified.")

                await session.commit()
            except Exception as e:
                logger.error(f"[blockchain] Failed to start blockchain subsystem: {e}")
                await session.rollback()
                self.error_count += 1
                raise e

        await event_bus.publish("ChainInitialized", {"height": 0}, sender="blockchain_subsystem")
        logger.info("[blockchain] Subsystem active.")

    async def health_check(self) -> bool:
        """Check the health of the blockchain manager and ledger."""
        if not self.manager:
            return False

        try:
            async with AsyncSessionLocal() as session:
                latest = await self.manager.get_latest_block(session)
                return latest is not None
        except Exception:
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
