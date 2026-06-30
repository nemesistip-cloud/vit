import logging
import os
import asyncio
from typing import Dict, Any
from app.core.kernel import Subsystem, kernel
from app.db.database import AsyncSessionLocal, engine, Base
from app.modules.wallet.models import PlatformConfig
from sqlalchemy import select, text
from app.config import APP_NAME, APP_VERSION, ENVIRONMENT, REDIS_URL, print_config_status
from app.services.firestore_events import setup_firestore_events
from app.tasks.telegram_digest import start_telegram_digest
from app.tasks.settlement_task import start_settlement_worker
from app.tasks.ticker_sync import start_ticker_sync

logger = logging.getLogger(__name__)

class ConfigSubsystem(Subsystem):
    name = "config"
    dependencies = []

    async def _on_initialize(self, config: Dict[str, Any]):
        # Load environment variables into kernel config
        self.kernel.config["app_name"] = APP_NAME
        self.kernel.config["app_version"] = APP_VERSION
        self.kernel.config["environment"] = ENVIRONMENT

        # Load secrets from GCP (placeholder for Track-006)
        from app.core.secrets_loader import load_all_secrets
        await load_all_secrets()

        # Load integration keys from DB
        try:
            async with AsyncSessionLocal() as db:
                rows = (await db.execute(
                    select(PlatformConfig).where(PlatformConfig.key.like("integration:%"))
                )).scalars().all()
                for row in rows:
                    env_key = row.key.replace("integration:", "")
                    if env_key and not os.environ.get(env_key):
                        val = row.value
                        if isinstance(val, dict):
                            val = val.get("value", val)
                            if isinstance(val, dict):
                                import json
                                val = json.dumps(val)
                        os.environ[env_key] = str(val)
            if rows:
                logger.info(f"[kernel] Loaded {len(rows)} integration key(s) from DB")
        except Exception:
            pass

        logger.info(f"[kernel] Configuration loaded for {APP_NAME} v{APP_VERSION} ({ENVIRONMENT})")

class DatabaseSubsystem(Subsystem):
    name = "database"
    dependencies = ["config"]

    async def _on_start(self):
        # Verify database connectivity
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

        # Ensure schema initialization (Bootstrap logic)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("[kernel] Database connectivity verified and schema synchronized.")

    async def health_check(self) -> bool:
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"[kernel] Database health check failed: {e}")
            return False

class RedisSubsystem(Subsystem):
    name = "redis"
    dependencies = ["config"]

    async def _on_start(self):
        from app.core.redis import require_redis
        # Mock app for legacy compatibility if needed
        class MockApp:
            state = type('State', (), {'redis': None})
        await require_redis(MockApp())
        logger.info("[kernel] Redis configured.")

class AISubsystem(Subsystem):
    name = "ai"
    dependencies = ["config", "database"]

    async def _on_start(self):
        from app.services.ai_client import provider_status
        await provider_status()
        logger.info("[kernel] AI Intelligence system initialized.")

class TaskSubsystem(Subsystem):
    name = "tasks"
    dependencies = ["database", "redis"]

    async def _on_start(self):
        start_ticker_sync()
        start_settlement_worker()
        start_telegram_digest()
        logger.info("[kernel] Background task workers started.")

class PlatformSubsystem(Subsystem):
    name = "platform"
    dependencies = ["tasks", "ai"]

    async def _on_start(self):
        setup_firestore_events()
        print_config_status()
        logger.info("[kernel] Platform OS features active.")

def register_core_subsystems():
    kernel.register_subsystem(ConfigSubsystem)
    kernel.register_subsystem(DatabaseSubsystem)
    kernel.register_subsystem(RedisSubsystem)
    kernel.register_subsystem(AISubsystem)
    kernel.register_subsystem(TaskSubsystem)
    kernel.register_subsystem(PlatformSubsystem)
