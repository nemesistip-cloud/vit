import logging
import os
import asyncio
from typing import Dict, Any
from app.core.kernel import Subsystem, kernel
from app.db.database import AsyncSessionLocal, engine, Base
from sqlalchemy import text
from app.core.config.manager import config_manager

logger = logging.getLogger(__name__)

class ConfigSubsystem(Subsystem):
    """
    Subsystem responsible for bridging the new ConfigurationManager
    with legacy code and ensuring configuration is ready.
    """
    name = "config"
    dependencies = []

    async def _on_initialize(self, config: Dict[str, Any]):
        # Configuration is already loaded by the Kernel before initializing modules.
        # This subsystem now acts as a diagnostic bridge.
        vit_config = config_manager.config

        # Log effective environment
        logger.info(f"[kernel] Configuration active: {vit_config.app.name} v{vit_config.app.version} ({vit_config.app.environment.value})")

        # Diagnostic report
        diag = config_manager.get_diagnostics()
        logger.debug(f"[kernel] Configuration Diagnostics: {diag}")

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
        from app.tasks.ticker_sync import start_ticker_sync
        from app.tasks.settlement_task import start_settlement_worker
        from app.tasks.telegram_digest import start_telegram_digest

        start_ticker_sync()
        start_settlement_worker()
        start_telegram_digest()
        logger.info("[kernel] Background task workers started.")

class PlatformSubsystem(Subsystem):
    name = "platform"
    dependencies = ["tasks", "ai"]

    async def _on_start(self):
        from app.services.firestore_events import setup_firestore_events
        from app.config import print_config_status

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
