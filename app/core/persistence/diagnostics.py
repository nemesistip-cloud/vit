import logging
import time
from typing import Dict, Any
from app.core.persistence.repository import RepositoryRegistry

logger = logging.getLogger(__name__)

class PersistenceDiagnostics:
    """Provides detailed diagnostic information about the persistence platform."""

    def __init__(self, persistence_manager):
        self.manager = persistence_manager

    async def get_report(self) -> Dict[str, Any]:
        """Generate a complete diagnostic report."""
        from app.db.database import engine

        # Connection pool stats
        pool = engine.pool
        pool_stats = {
            "size": pool.size() if hasattr(pool, 'size') else 0,
            "checkedin": pool.checkedin() if hasattr(pool, 'checkedin') else 0,
            "checkedout": pool.checkedout() if hasattr(pool, 'checkedout') else 0,
            "overflow": pool.overflow() if hasattr(pool, 'overflow') else 0,
        }

        return {
            "status": "HEALTHY" if await self.manager.health_check() else "UNHEALTHY",
            "uptime": round(time.time() - self.manager._start_time, 2),
            "connection_pool": pool_stats,
            "repositories": {
                "count": len(RepositoryRegistry.list_repositories()),
                "list": RepositoryRegistry.list_repositories()
            },
            "error_count": self.manager.error_count
        }
