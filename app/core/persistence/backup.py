import logging
import asyncio
import os
import shutil
from typing import Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.engine import make_url

logger = logging.getLogger(__name__)

class BackupManager:
    """Manages database backups and retention policies."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backup_path = config.get("persistence", {}).get("backup_path", "./backups")

    async def create_backup(self, label: str = "manual") -> str:
        """Trigger a database backup."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"vit_backup_{label}_{timestamp}.sql"
        backup_dir = Path(self.backup_path).resolve()
        backup_dir.mkdir(parents=True, exist_ok=True)
        output = backup_dir / filename
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url or shutil.which("pg_dump") is None:
            raise RuntimeError("PostgreSQL backup requires DATABASE_URL and pg_dump")
        url = make_url(database_url)
        if url.get_backend_name() != "postgresql":
            raise RuntimeError("Automatic backup currently supports PostgreSQL only")
        env = os.environ.copy()
        if url.password:
            env["PGPASSWORD"] = url.password
        host = url.host or "localhost"
        port = str(url.port) if url.port else "5432"
        command = ["pg_dump", "--format=plain", "--file", str(output), "--host", host, "--port", port, "--username", url.username or "", url.database or ""]
        process = await asyncio.create_subprocess_exec(*command, env=env, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()
        if process.returncode != 0:
            output.unlink(missing_ok=True)
            raise RuntimeError(f"pg_dump failed: {stderr.decode(errors='replace')[:500]}")
        return str(output)

    async def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups."""
        backup_dir = Path(self.backup_path).resolve()
        if not backup_dir.exists():
            return []
        return [{"filename": path.name, "size_bytes": path.stat().st_size, "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()} for path in sorted(backup_dir.glob("vit_backup_*.sql"), key=lambda item: item.stat().st_mtime, reverse=True)]

    async def verify_backup(self, filename: str) -> bool:
        """Verify the integrity of a backup file."""
        path = Path(self.backup_path).resolve() / filename
        return path.is_file() and path.stat().st_size > 0 and path.name == filename and path.suffix == ".sql"

class RecoveryManager:
    """Handles data recovery and restoration from backups."""

    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager

    async def restore_backup(self, filename: str) -> bool:
        """Restore the database from a backup file."""
        logger.warning(f"[persistence] CRITICAL: Starting database restoration from {filename}")

        # Verify first
        if not await self.backup_manager.verify_backup(filename):
            logger.error("[persistence] Restore aborted: Backup verification failed.")
            return False

        database_url = os.getenv("DATABASE_URL", "")
        if not database_url or shutil.which("psql") is None:
            raise RuntimeError("PostgreSQL restore requires DATABASE_URL and psql")
        url = make_url(database_url)
        if url.get_backend_name() != "postgresql":
            raise RuntimeError("Automatic restore currently supports PostgreSQL only")
        path = Path(self.backup_manager.backup_path).resolve() / filename
        env = os.environ.copy()
        if url.password:
            env["PGPASSWORD"] = url.password
        command = ["psql", "--host", url.host or "localhost", "--port", str(url.port or 5432), "--username", url.username or "", "--dbname", url.database or "", "--file", str(path)]
        process = await asyncio.create_subprocess_exec(*command, env=env, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"psql restore failed: {stderr.decode(errors='replace')[:500]}")
        return True
