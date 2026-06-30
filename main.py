# main.py — VIT Analytics Platform v5.6.0
# Fully orchestrated via VIT Runtime Kernel & Module Registry

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.config import APP_NAME, APP_VERSION, get_env
from app.core.kernel import kernel, setup_signal_handlers
from app.core.subsystems import register_core_subsystems

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Register Core Subsystems
    await register_core_subsystems()

    # 2. Boot VIT Runtime Kernel
    setup_signal_handlers()
    await kernel.boot()

    print(f"🚀 VIT Network v{APP_VERSION} starting (KERNEL MODE)...")

    yield
    # 3. Shutdown VIT Runtime Kernel
    await kernel.shutdown()
    print("🛑 Shutdown complete")

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan
)

@app.get("/ping")
async def ping():
    return {"status": "ok", "kernel": kernel.state.value}

@app.get("/api/system/kernel", tags=["System"])
async def get_kernel_status():
    return kernel.get_status()

# (Simulating other route registrations for track completion)
from app.auth.routes import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

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

    return summary
