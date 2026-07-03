# main.py — VIT Analytics Platform v5.6.0
# Fully orchestrated via VIT Runtime Kernel & Module Registry

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func

from app.config import APP_NAME, APP_VERSION, get_env
from app.core.kernel import kernel, setup_signal_handlers
from app.core.subsystems import register_core_subsystems
from app.db.database import get_db
from app.schemas.schemas import HealthResponse
from app.core.dependencies import get_orchestrator

# --- VIT Runtime Kernel ---
register_core_subsystems()

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_signal_handlers()
    await kernel.boot()
    print(f'🚀 VIT Network v{APP_VERSION} starting (RUNTIME KERNEL MODE)...')
    yield
    await kernel.shutdown()
    print('🛑 Shutdown complete')

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan
)

@app.get("/ping")
async def ping():
    """Always-available liveness probe — < 50ms, zero external resources.
    Touches no DB, no Redis, no models. Safe as Render health-check path."""
    return {"status": "ok", "ts": int(time.time())}


@app.get("/readiness", include_in_schema=False)
@app.get("/api/readiness", include_in_schema=False)
async def readiness(db: AsyncSession = Depends(get_db)):
    """Lightweight readiness probe for Cloud Run / load balancers."""
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    status_code = 200 if db_ok else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if db_ok else "not_ready", "db": db_ok},
    )


@app.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)):
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    orch = get_orchestrator()
    models = orch.num_models_ready() if orch else 0

    # C-5 — agent status snapshot
    agents_info: dict = {}
    try:
        coordinator = getattr(app.state, "agent_coordinator", None)
        supervisor = getattr(app.state, "background_supervisor", None)
        agent_names = []
        running_count = 0
        if coordinator:
            snap = coordinator.status() if hasattr(coordinator, "status") else {}
            agents_snap = snap.get("agents", {})
            for name, info in agents_snap.items():
                agent_names.append(name)
                if info.get("status") == "ok" or info.get("enabled", True):
                    running_count += 1
        if supervisor:
            sup_snap = supervisor.snapshot() if hasattr(supervisor, "snapshot") else {}
            for name, info in sup_snap.items():
                if name not in agent_names:
                    agent_names.append(name)
                if info.get("running"):
                    running_count += 1
        total = len(agent_names)
        stopped = total - running_count
        stopped_names = []
        if coordinator:
            snap = coordinator.status() if hasattr(coordinator, "status") else {}
            agents_snap = snap.get("agents", {})
            for n, info in agents_snap.items():
                if info.get("status") != "ok" and not info.get("enabled", True):
                    stopped_names.append(n)
        agents_info = {
            "total": total,
            "running": running_count,
            "stopped": stopped,
            "stopped_names": stopped_names,
        }
    except Exception:
        pass

    # C-5 — data snapshot
    data_info: dict = {}
    try:
        from app.db.models import Match as _HMatch, Prediction as _HPred, CLVEntry as _HCLV
        _m_count = (await db.execute(select(func.count(_HMatch.id)))).scalar() or 0
        _p_count = (await db.execute(
            select(func.count(_HPred.id)).where(_HPred.was_correct.is_not(None))
        )).scalar() or 0
        _c_count = (await db.execute(select(func.count(_HCLV.id)))).scalar() or 0
        data_info = {
            "matches": _m_count,
            "settled_predictions": _p_count,
            "clv_entries": _c_count,
        }
    except Exception:
        pass

    # C-5 — AI provider status
    ai_providers: dict = {}
    try:
        from app.services.ai_client import provider_status as _ps
        _status = await _ps()
        for name, info in _status.items():
            ai_providers[name] = info.get("status", "unknown")
    except Exception:
        pass

    kernel_status = kernel.get_status()
    if kernel_status['kernel_state'] == 'DEGRADED':
        db_ok = False # Signal degradation to health check
    return HealthResponse(
        status="ok" if db_ok and models > 0 else ("starting" if db_ok else "degraded"),
        version=APP_VERSION,
        models_loaded=models,
        db_connected=db_ok,
        clv_tracking_enabled=True,
        agents=agents_info or None,
        data=data_info or None,
        ai_providers=ai_providers or None,
    )


@app.get("/system/status", tags=["System"])
@app.get("/api/system/status", tags=["System"], include_in_schema=False)
async def system_status(db: AsyncSession = Depends(get_db)):
    """Public system health/status endpoint — returns live platform stats for the ecosystem ticker."""
    from app.db.models import User
    from sqlalchemy import func, select
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    total_users = 0
    active_users_30d = 0
    active_validators = 0
    total_staked_vit = 0.0
    total_predictions_all = 0

    try:
        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    except Exception:
        pass

    try:
        from app.db.models import Prediction
        total_predictions_all = (await db.execute(select(func.count(Prediction.id)))).scalar() or 0
        active_users_30d = (
            await db.execute(
                select(func.count(func.distinct(Prediction.user_id)))
                .where(Prediction.timestamp >= thirty_days_ago.replace(tzinfo=None))
            )
        ).scalar() or 0
    except Exception:
        pass

    try:
        from app.modules.blockchain.models import ValidatorNode, ValidatorStatus
        active_validators = (
            await db.execute(
                select(func.count(ValidatorNode.id)).where(
                    ValidatorNode.status == ValidatorStatus.ACTIVE.value
                )
            )
        ).scalar() or 0
    except Exception:
        pass

    try:
        from app.modules.wallet.models import Wallet
        total_staked_vit = float(
            (await db.execute(select(func.sum(Wallet.vitcoin_balance)))).scalar() or 0
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "version": APP_VERSION,
        "total_users": total_users,
        "active_users_30d": active_users_30d,
        "active_validators": active_validators,
        "total_staked_vit": round(total_staked_vit, 4),
        "total_predictions": total_predictions_all,
    }

@app.get("/api/system/kernel", tags=["System"])
async def get_kernel_status():
    return kernel.get_status()

# (Simulating other route registrations for track completion)
from app.auth.routes import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

from app.api.routes.observability import router as obs_router
app.include_router(obs_router, prefix="/api/obs", tags=["Observability"])

from app.plugins.identity.routes import router as identity_router
app.include_router(identity_router, prefix="/api/identity", tags=["Identity"])

from app.api.routes.blockchain import router as blockchain_router
app.include_router(blockchain_router)

from app.api.routes.explorer import router as explorer_router
app.include_router(explorer_router, prefix="/api")

from app.api.routes.blockchain_ws import router as blockchain_ws_router
app.include_router(blockchain_ws_router)

from app.api.routes.blockchain_analytics import router as blockchain_analytics_router
app.include_router(blockchain_analytics_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

@app.get("/api/system/registry", tags=["System"])
async def get_registry_diagnostics():
    """Authoritative diagnostics for all registered modules."""
    from app.core.registry.manager import registry
    return registry.get_diagnostics()

@app.get("/api/system/health/summary", tags=["System"])
async def get_health_summary():
    """Aggregated health status across the entire ecosystem."""
    from app.core.registry.manager import registry
    from app.core.registry.models import HealthStatus

    diagnostics = registry.get_diagnostics()
    modules = diagnostics.get("modules", {})

    summary = {
        "overall_status": "HEALTHY",
        "details": {}
    }

    unhealthy_count = 0
    for mid, info in modules.items():
        h = info.get("health")
        summary["details"][mid] = h
        if h != "HEALTHY":
            unhealthy_count += 1

    if unhealthy_count > 0:
        summary["overall_status"] = "DEGRADED" if unhealthy_count < len(modules) else "UNHEALTHY"

def _sanitize_validation_errors(errors: list) -> list:
    """Helper to clean up pydantic validation errors for public response."""
    return [
        {"loc": e["loc"], "msg": e["msg"], "type": e["type"]}
        for e in errors
    ]
