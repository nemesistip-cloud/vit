import asyncio
import os
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool


@pytest.mark.asyncio
async def test_lifespan_bootstrap_creates_schema_for_new_sqlite_db(tmp_path, monkeypatch):
    import app.db.database as database_module
    import main as main_module

    db_path = tmp_path / "vit-bootstrap.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

    orig_engine = database_module.engine
    orig_session_local = database_module.AsyncSessionLocal

    new_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
        future=True,
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )
    database_module.engine = new_engine
    database_module.AsyncSessionLocal = async_sessionmaker(
        new_engine, expire_on_commit=False, class_=AsyncSession
    )

    try:
        async with main_module.lifespan(main_module.app):
            for _ in range(50):
                await asyncio.sleep(0.1)
                async with database_module.AsyncSessionLocal() as session:
                    res = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
                    if res.scalar_one_or_none() == "users":
                        break

        async with database_module.AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
            assert result.scalar_one_or_none() == "users"
    finally:
        await new_engine.dispose()
        database_module.engine = orig_engine
        database_module.AsyncSessionLocal = orig_session_local


@pytest.mark.asyncio
async def test_lifespan_starts_when_signal_handlers_are_unavailable(monkeypatch):
    import main as main_module

    def raise_runtime_error(self, sig, callback):
        raise RuntimeError("set_wakeup_fd only works in main thread of the main interpreter")

    monkeypatch.setattr(asyncio.AbstractEventLoop, "add_signal_handler", raise_runtime_error)

    async with main_module.lifespan(main_module.app):
        pass


@pytest.mark.asyncio
async def test_lifespan_bootstraps_admin_on_startup(monkeypatch):
    import main as main_module

    admin_bootstrap_called = asyncio.Event()

    async def fake_bootstrap():
        admin_bootstrap_called.set()

    monkeypatch.setattr(main_module, "bootstrap_default_admin", fake_bootstrap)

    async with main_module.lifespan(main_module.app):
        await asyncio.wait_for(admin_bootstrap_called.wait(), timeout=2)


@pytest.mark.asyncio
async def test_lifespan_cancels_background_boot_and_watchdog(monkeypatch):
    import app.db.database as database_module
    import main as main_module

    monkeypatch.setattr(database_module, "initialize_schema", AsyncMock())
    monkeypatch.setattr(main_module.kernel, "shutdown", AsyncMock())
    boot_started = asyncio.Event()
    watchdog_started = asyncio.Event()

    async def blocked_boot():
        boot_started.set()
        await asyncio.Event().wait()

    async def blocked_watchdog(_stop_event):
        watchdog_started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(main_module.kernel, "boot", blocked_boot)
    monkeypatch.setattr(main_module, "_watchdog_loop", blocked_watchdog)

    async with main_module.lifespan(main_module.app):
        await asyncio.wait_for(boot_started.wait(), timeout=2)
        await asyncio.wait_for(watchdog_started.wait(), timeout=2)

    background_tasks = {
        task.get_name()
        for task in asyncio.all_tasks()
        if task is not asyncio.current_task()
    }
    assert "kernel-boot" not in background_tasks
    assert "service-watchdog" not in background_tasks
