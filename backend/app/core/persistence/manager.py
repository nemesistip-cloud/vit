import logging
import time
from typing import Dict, Any, List
from app.core.kernel import Subsystem
from app.core.registry.models import ModuleMetadata, HealthStatus
from app.core.persistence.repository import RepositoryRegistry

logger = logging.getLogger(__name__)

class PersistenceManager(Subsystem):
    """Authoritative entry point for the VIT Persistence & Data Platform."""

    name = "persistence"
    dependencies = ["config", "observability", "database"]

    def __init__(self, kernel):
        super().__init__(kernel)
        self._metadata = ModuleMetadata(
            module_id=self.name,
            name="Persistence Platform",
            owner="core",
            domain="infrastructure",
            version="1.1.0",
            capabilities=[
                "PersistenceProvider",
                "RepositoryProvider",
                "TransactionProvider",
                "CacheProvider",
                "MigrationProvider",
                "AuditProvider"
            ],
            dependencies=self.dependencies
        )
        self._start_time = 0.0

    async def _on_initialize(self, config: Dict[str, Any]):
        """Initialize the persistence platform."""
        logger.info("[persistence] Initializing Persistence & Data Platform...")
        # Discovery/registration of core repositories could happen here
        self._start_time = time.time()

    async def _on_start(self):
        """Start persistence services."""
        logger.info("[persistence] Persistence Platform active.")

        # Verify connectivity via TransactionManager
        from app.core.persistence.transaction import TransactionManager
        try:
            async def ping(uow):
                from sqlalchemy import text
                await uow.session.execute(text("SELECT 1"))
            await TransactionManager.run_in_transaction(ping)
            logger.info("[persistence] Database connectivity verified via TransactionManager.")
        except Exception as e:
            logger.error(f"[persistence] Database connectivity check failed: {e}")
            self.error_count += 1

    async def health_check(self) -> bool:
        """Check the health of the persistence platform."""
        try:
            from app.db.database import AsyncSessionLocal
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"[persistence] Health check failed: {e}")
            return False

    async def get_diagnostics(self) -> Dict[str, Any]:
        """Return runtime diagnostics for the persistence platform."""
        diags = await super().get_diagnostics()
        diags.update({
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "registered_repositories": RepositoryRegistry.list_repositories(),
        })
        return diags
