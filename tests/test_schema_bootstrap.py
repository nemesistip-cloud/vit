import asyncio
import importlib
import os

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_lifespan_bootstrap_creates_schema_for_new_sqlite_db(tmp_path, monkeypatch):
    db_path = tmp_path / "vit-bootstrap.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

    import app.db.database as database_module
    import main as main_module

    importlib.reload(database_module)
    importlib.reload(main_module)

    async with main_module.lifespan(main_module.app):
        pass

    async with database_module.AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
        assert result.scalar_one_or_none() == "users"


@pytest.mark.asyncio
async def test_lifespan_starts_when_signal_handlers_are_unavailable(monkeypatch):
    import main as main_module

    def raise_runtime_error(self, sig, callback):
        raise RuntimeError("set_wakeup_fd only works in main thread of the main interpreter")

    monkeypatch.setattr(asyncio.AbstractEventLoop, "add_signal_handler", raise_runtime_error)

    async with main_module.lifespan(main_module.app):
        pass
