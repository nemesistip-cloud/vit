import logging
import os
import asyncio
from typing import Dict, Any
from app.core.kernel import Subsystem, kernel
from app.core.authorization.subsystem import AuthorizationSubsystem
from app.core.resource_platform.subsystem import ResourcePlatformSubsystem
from vit_chain.core.subsystem import BlockchainSubsystem
from app.core.wallet.subsystem import WalletSubsystem
from app.db.database import AsyncSessionLocal, engine, Base
from sqlalchemy import text
from app.core.config.manager import config_manager

logger = logging.getLogger(__name__)

class ObservabilitySubsystem(Subsystem):
    name = "observability"
    dependencies = ["config"]

    async def _on_initialize(self, config: Dict[str, Any]):
        from app.core.observability.manager import obs_manager
        from app.core.observability.logger import setup_observability_logging

        # Configure logging first
        log_level = config.get("app", {}).get("log_level", "INFO")
        setup_observability_logging(log_level)

        await obs_manager.initialize(config)
        logger.info("[kernel] Observability platform integrated.")

    async def _on_start(self):
        from app.core.observability.manager import obs_manager
        from app.core.observability.models import HealthStatus

        obs_manager.record_metric("kernel_boot_start", 1.0)
        obs_manager.health.update_status("kernel", HealthStatus.HEALTHY, "Kernel is starting")

    async def health_check(self) -> bool:
        # NOTE: this must check the observability platform's OWN liveness,
        # not the aggregate status of every other subsystem. It used to
        # mirror obs_manager.health.get_overall_status(), which meant a
        # single unrelated unhealthy subsystem (e.g. blockchain) made
        # "observability" itself report UNHEALTHY too, masking the real
        # offender in dashboards and diagnostics.
        from app.core.observability.manager import obs_manager

        try:
            obs_manager.record_metric("observability_self_check", 1.0)
            return True
        except Exception:
            return False

class ConfigSubsystem(Subsystem):
    name = "config"
    dependencies = []

    async def _on_initialize(self, config: Dict[str, Any]):
        vit_config = config_manager.config
        env_val = getattr(vit_config.app.environment, 'value', str(vit_config.app.environment))
        logger.info(f"[kernel] Configuration active: {vit_config.app.name} v{vit_config.app.version} ({env_val})")

class DatabaseSubsystem(Subsystem):
    name = "database"
    dependencies = ["config", "observability"]

    async def _on_start(self):
        from app.core.observability.manager import obs_manager
        from app.core.observability.models import HealthStatus

        # Import module models referenced by User's SQLAlchemy relationships
        # (string-based refs like "StudentProfile", "UserTaskCompletion", etc.)
        # so mapper configuration succeeds before the first ORM query.
        # This runs after all routers have been imported at module level.
        try:
            import app.modules.identity.models        # noqa: F401
            import app.modules.tasks.models           # noqa: F401
            import app.modules.notifications.models   # noqa: F401
            import app.modules.trust.models           # noqa: F401
            from sqlalchemy.orm import configure_mappers
            configure_mappers()
        except Exception as _e:
            logger.warning("[kernel] configure_mappers warning (non-fatal): %s", _e)

        start = asyncio.get_event_loop().time()
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        duration = asyncio.get_event_loop().time() - start
        obs_manager.record_metric("database_init_time_ms", duration * 1000)
        obs_manager.health.update_status("database", HealthStatus.HEALTHY, "Connected")
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
    dependencies = ["config", "observability"]

    async def _on_start(self):
        from app.core.redis import require_redis
        from app.core.observability.manager import obs_manager
        from app.core.observability.models import HealthStatus

        class MockApp:
            state = type('State', (), {'redis': None})
        await require_redis(MockApp())
        obs_manager.health.update_status("redis", HealthStatus.HEALTHY, "Connected")
        logger.info("[kernel] Redis configured.")

class AISubsystem(Subsystem):
    name = "ai"
    dependencies = ["config", "database", "observability"]

    async def _on_start(self):
        from app.services.ai_client import provider_status
        from app.core.observability.manager import obs_manager
        from app.core.observability.models import HealthStatus

        status = await provider_status()
        obs_manager.health.update_status("ai", HealthStatus.HEALTHY, "Providers online", details=status)
        logger.info("[kernel] AI Intelligence system initialized.")

class TaskSubsystem(Subsystem):
    name = "tasks"
    dependencies = ["database", "redis", "observability"]

    async def _on_start(self):
        try:
            from app.tasks.ticker_sync import start_ticker_sync
            from app.tasks.settlement_task import start_settlement_worker
            from app.tasks.telegram_digest import start_telegram_digest
            from app.core.observability.manager import obs_manager
            from app.core.observability.models import HealthStatus

            start_ticker_sync()
            start_settlement_worker()
            start_telegram_digest()
            obs_manager.health.update_status("tasks", HealthStatus.HEALTHY, "Workers started")
            logger.info("[kernel] Background task workers started.")
        except ImportError as e:
            logger.warning(f"[kernel] Task subsystem partially started (some tasks unavailable): {e}")
            from app.core.observability.manager import obs_manager
            from app.core.observability.models import HealthStatus
            obs_manager.health.update_status("tasks", HealthStatus.DEGRADED, f"Import error: {e}")

class PlatformSubsystem(Subsystem):
    name = "platform"
    dependencies = ["tasks", "ai", "observability"]

    async def _on_start(self):
        try:
            from app.services.firestore_events import setup_firestore_events
            from app.config import print_config_status
            from app.core.observability.manager import obs_manager
            from app.core.observability.models import HealthStatus

            setup_firestore_events()
            print_config_status()
            obs_manager.health.update_status("platform", HealthStatus.HEALTHY, "Active")
            logger.info("[kernel] Platform OS features active.")
        except Exception as e:
            logger.warning(f"[kernel] Platform subsystem failed to start fully: {e}")

        # Integrate and serve production React SPA frontend
        try:
            import os
            import sys
            from fastapi.responses import FileResponse, Response
            from fastapi import Request

            main_module = sys.modules.get("main")
            if main_module and hasattr(main_module, "app"):
                app = main_module.app

                # Dynamically register actual notification routes to bypass main.py mocks and fix tests
                try:
                    from app.modules.notifications.routes import router as notifications_router
                    from app.modules.notifications.websocket import router as notifications_ws_router
                    app.include_router(notifications_router)
                    app.include_router(notifications_ws_router)
                except Exception as e:
                    logger.error(f"[kernel] Failed to dynamically include notification routes: {e}")

                # Dynamically register actual modules AI routes to bypass main.py limitations
                try:
                    from app.modules.ai.routes import router as ai_module_router
                    app.include_router(ai_module_router)
                except Exception as e:
                    logger.error(f"[kernel] Failed to dynamically include modules AI routes: {e}")

                # Dynamically register Tachyon VESS API router
                try:
                    from tachyon.api.router import router as tachyon_router
                    app.include_router(tachyon_router, prefix="/api/tachyon")
                except Exception as e:
                    logger.error(f"[kernel] Failed to dynamically include tachyon routes: {e}")

                # Remove default root route ("/") and explorer mount from main.py to allow unified SPA fallback serving
                for r in list(app.routes):
                    if getattr(r, "path", None) in ["/", "/explorer"]:
                        app.routes.remove(r)

                frontend_path = "frontend/dist"
                explorer_path = "explorer/dist"

                frontend_base = os.path.abspath(frontend_path) if os.path.exists(frontend_path) else None
                explorer_base = os.path.abspath(explorer_path) if os.path.exists(explorer_path) else None

                if frontend_base:
                    # Secure and unified SPA Fallback Router
                    @app.get("/{catchall:path}", include_in_schema=False)
                    async def frontend_spa_fallback(catchall: str, request: Request):
                        clean_path = catchall.strip("/")

                        # 1. Prevent fallbacks for dynamic API routes, documentation, and system health checks
                        if clean_path.startswith("api/") or clean_path in ["docs", "openapi.json", "health", "ping"]:
                            return Response(status_code=404, content="Not Found")

                        # 2. Block Explorer SPA fallback routing
                        if clean_path.startswith("explorer"):
                            sub_path = clean_path[len("explorer"):].strip("/")
                            if explorer_base:
                                # Securely resolve and verify the absolute path to prevent directory traversal
                                file_on_disk = os.path.abspath(os.path.join(explorer_base, sub_path))
                                if sub_path and file_on_disk.startswith(explorer_base) and os.path.exists(file_on_disk) and os.path.isfile(file_on_disk):
                                    return FileResponse(file_on_disk)
                                return FileResponse(os.path.join(explorer_base, "index.html"))
                            return Response(status_code=404, content="Explorer Not Found")

                        # 3. Main Frontend SPA routing
                        # Securely resolve and verify the absolute path to prevent directory traversal
                        file_on_disk = os.path.abspath(os.path.join(frontend_base, clean_path))
                        if clean_path and file_on_disk.startswith(frontend_base) and os.path.exists(file_on_disk) and os.path.isfile(file_on_disk):
                            return FileResponse(file_on_disk)

                        # Default main portal fallback
                        return FileResponse(os.path.join(frontend_base, "index.html"))

                    logger.info(f"[kernel] Production frontend and explorer SPAs successfully integrated")
                else:
                    logger.warning(f"[kernel] Production frontend build {frontend_path} not found. Serve disabled.")
        except Exception as e:
            logger.error(f"[kernel] Failed to mount production frontend SPA: {e}")


class PluginSubsystem(Subsystem):
    name = "plugins"
    dependencies = ["config", "observability", "database"]

    async def _on_initialize(self, config: Dict[str, Any]):
        from app.core.plugins.manager import plugin_manager
        await plugin_manager.bootstrap()
        logger.info("[kernel] Plugin framework discovered and loaded extensions.")

    async def _on_start(self):
        from app.core.plugins.manager import plugin_manager
        from app.core.observability.manager import obs_manager
        from app.core.observability.models import HealthStatus

        await plugin_manager.activate_all()

        # Report status to observability
        diags = plugin_manager.get_diagnostics()
        obs_manager.health.update_status("plugins", HealthStatus.HEALTHY, f"Active ({diags['total_plugins']} plugins)")
        logger.info("[kernel] All plugins activated and running.")

    async def _on_stop(self):
        from app.core.plugins.manager import plugin_manager
        await plugin_manager.shutdown_all()
        logger.info("[kernel] Plugin framework shut down.")

    async def health_check(self) -> bool:
        from app.core.plugins.manager import plugin_manager
        from app.core.plugins.models import PluginStatus

        diags = plugin_manager.get_diagnostics()
        # Subsystem is degraded if any plugin is in FAILING state
        for pid, info in diags['plugins'].items():
            if info['status'] == PluginStatus.FAILING.value:
                return False
        return True


class GenesisSubsystem(Subsystem):
    """
    Phase 1 gate: seeds the VIT Chain genesis block on first boot.
    Idempotent — safe to run on every restart; skips if genesis already present.
    Depends on DatabaseSubsystem to ensure tables exist before seeding.
    """
    name         = "genesis"
    dependencies = ["database"]

    async def _on_start(self):
        from app.db.database import AsyncSessionLocal
        from vit_chain.core.genesis import seed_genesis
        from app.core.observability.manager import obs_manager
        from app.core.observability.models import HealthStatus
        try:
            async with AsyncSessionLocal() as db:
                seeded = await seed_genesis(db)
            msg = "Genesis block seeded (first boot)" if seeded else "Genesis block already present"
            logger.info("[kernel] %s", msg)
            obs_manager.health.update_status(self.name, HealthStatus.HEALTHY, msg)
        except Exception as exc:
            logger.error("[kernel] Genesis seeding failed (non-fatal): %s", exc)
            obs_manager.health.update_status(self.name, HealthStatus.UNHEALTHY, str(exc))

    async def health_check(self) -> bool:
        return True

def register_core_subsystems():
    from app.core.persistence.manager import PersistenceManager
    kernel.register_subsystem(PersistenceManager)
    kernel.register_subsystem(ResourcePlatformSubsystem)
    kernel.register_subsystem(ObservabilitySubsystem)
    kernel.register_subsystem(ConfigSubsystem)
    kernel.register_subsystem(DatabaseSubsystem)
    kernel.register_subsystem(GenesisSubsystem)
    kernel.register_subsystem(AuthorizationSubsystem)
    kernel.register_subsystem(RedisSubsystem)
    kernel.register_subsystem(AISubsystem)
    kernel.register_subsystem(TaskSubsystem)
    kernel.register_subsystem(PlatformSubsystem)
    kernel.register_subsystem(PluginSubsystem)
    kernel.register_subsystem(BlockchainSubsystem)
    kernel.register_subsystem(WalletSubsystem)
