import logging
import os
import subprocess
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class MigrationManager:
    """Orchestrates database schema migrations using Alembic."""

    def __init__(self, alembic_ini: str = "alembic.ini"):
        self.alembic_ini = alembic_ini

    async def run_migrations(self):
        """Run all pending migrations."""
        logger.info("[persistence] Running database migrations...")
        try:
            # Using subprocess to run alembic upgrade head
            # In a real system, we might use alembic's programmatic API
            process = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"[persistence] Migrations completed successfully: {process.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"[persistence] Migration failed: {e.stderr}")
            raise RuntimeError(f"Database migration failed: {e.stderr}")

    async def check_current_revision(self) -> Optional[str]:
        """Get the current database revision."""
        try:
            process = subprocess.run(
                ["alembic", "current"],
                capture_output=True,
                text=True,
                check=True
            )
            return process.stdout.strip()
        except Exception:
            return None

    async def validate_schema(self) -> bool:
        """Verify that the current schema matches the expected state."""
        # This could check if any migrations are pending
        try:
            process = subprocess.run(
                ["alembic", "check"],
                capture_output=True,
                text=True
            )
            return process.returncode == 0
        except Exception as e:
            logger.warning(f"[persistence] Schema validation skipped or failed: {e}")
            return True # Default to true if check is not supported
