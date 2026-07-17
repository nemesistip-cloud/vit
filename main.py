import os
import time
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from fastapi.exceptions import RequestValidationError
from app.core.errors import AppError, error_response

from app.config import APP_NAME, APP_VERSION, get_env, get_int_env, CORS_ALLOWED_ORIGINS, ENVIRONMENT
from app.core.kernel import kernel, setup_signal_handlers
from app.core.subsystems import register_core_subsystems
from app.db.database import get_db
from app.schemas.schemas import HealthResponse
from app.core.dependencies import get_orchestrator

# --- Middleware ---
from app.api.middleware.request_id import RequestIDMiddleware
from app.api.middleware.logging import LoggingMiddleware
from app.api.middleware.auth import APIKeyMiddleware
from app.api.middleware.security import SecurityHeadersMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware

# --- VIT Runtime Kernel ---
register_core_subsystems()

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_signal_handlers()
    await kernel.boot()
    # Phase 0: connect event bus Redis layer so events persist across restarts
    from app.core.event_bus import event_bus
    await event_bus.connect_redis()
    print(f'🚀 VIT Network v{APP_VERSION} starting (RUNTIME KERNEL MODE)...')
    yield
    await event_bus.disconnect_redis()
    await kernel.shutdown()
    print('🛑 Shutdown complete')

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan
)

# --- CORS ---
# In production, restrict to an explicit allowlist read from CORS_ALLOWED_ORIGINS
# (comma-separated, e.g. "https://vit.network,https://www.vit.network").
# Falls back to "*" only in non-production environments.
_log = logging.getLogger(__name__)
if CORS_ALLOWED_ORIGINS:
    _cors_origins = [o.strip() for o in CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
else:
    if ENVIRONMENT == "production":
        _log.warning(
            "CORS_ALLOWED_ORIGINS is not set in production — defaulting to '*'. "
            "Set CORS_ALLOWED_ORIGINS in the Render dashboard to restrict origins."
        )
    _cors_origins = ["*"]

# --- Global Middleware Registration ---
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(APIKeyMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return error_response(request=request, status_code=exc.status_code, code=exc.code, message=exc.message)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return error_response(
        request=request,
        status_code=422,
        code="validation_error",
        message="Request validation failed",
        details=exc.errors()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled error: {exc}", exc_info=True)
    return error_response(
        request=request,
        status_code=500,
        code="internal_error",
        message="An unexpected error occurred"
    )

@app.get("/")
async def root():
    return {
        "name": "VIT Platform",
        "status": "healthy",
        "version": APP_VERSION,
        "environment": os.getenv("ENVIRONMENT", "production"),
        "uptime": f"{round(time.time() - kernel.startup_time, 2)}s",
        "subsystems": list(kernel.subsystems.keys())
    }

@app.get("/ping")
async def ping():
    return {"status": "ok", "ts": int(time.time())}

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
                    ValidatorNode.status == "ACTIVE"
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

@app.get("/readiness", include_in_schema=False)
@app.get("/api/readiness", include_in_schema=False)
async def readiness(db: AsyncSession = Depends(get_db)):
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
    # db_connected must reflect the actual database connection only.
    # Do NOT fold in unrelated kernel/subsystem degradation here -- a
    # degraded blockchain/AI subsystem previously forced db_connected=False
    # even though Postgres was reachable, which misled dashboards into
    # showing "PostgreSQL DEGRADED" during unrelated incidents.
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    orch = get_orchestrator()
    models = orch.num_models_ready() if orch else 0

    kernel_status = kernel.get_status()
    kernel_degraded = kernel_status['kernel_state'] == 'DEGRADED'

    if not db_ok:
        overall_status = "degraded"
    elif kernel_degraded or models == 0:
        overall_status = "starting" if models == 0 and not kernel_degraded else "degraded"
    else:
        overall_status = "ok"

    return HealthResponse(
        status=overall_status,
        version=APP_VERSION,
        models_loaded=models,
        db_connected=db_ok,
        clv_tracking_enabled=True
    )

# --- Router Registrations ---
from app.auth.routes import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(auth_router, tags=["Auth-Compat"], include_in_schema=False)
app.include_router(auth_router, tags=["Auth-Legacy"], include_in_schema=False)

from app.api.routes.observability import router as obs_router
app.include_router(obs_router, prefix="/api/obs", tags=["Observability"])

from app.plugins.identity.routes import router as identity_router
app.include_router(identity_router, prefix="/api/identity", tags=["Identity"])

from app.api.routes.blockchain import router as blockchain_router
app.include_router(blockchain_router)

from app.modules.blockchain.routes import router as blockchain_module_router
app.include_router(blockchain_module_router)

from vit_chain.rpc.router import router as chain_rpc_router
app.include_router(chain_rpc_router)

from app.api.routes.explorer import router as explorer_router
app.include_router(explorer_router, prefix="/api")

from app.api.routes.blockchain_ws import router as blockchain_ws_router
app.include_router(blockchain_ws_router)

from app.api.routes.blockchain_analytics import router as blockchain_analytics_router
app.include_router(blockchain_analytics_router)

# --- Business & AI Routers ---
from app.api.routes.matches import router as matches_router
app.include_router(matches_router, prefix="/api")

from app.api.routes.predict import router as predict_router
app.include_router(predict_router, prefix="/api")
app.include_router(predict_router, tags=["Predict-Compat"], include_in_schema=False)

from app.api.routes.attestation import router as attestation_router
app.include_router(attestation_router)

from app.api.routes.payout_verify import router as payout_verify_router
app.include_router(payout_verify_router)

from app.api.routes.multichain import router as multichain_router
app.include_router(multichain_router, tags=["Multichain"])

from app.api.routes.dashboard import router as dashboard_router
app.include_router(dashboard_router)

from app.api.routes.sports import router as sports_router
app.include_router(sports_router, prefix="/api")
app.include_router(sports_router, tags=["Sports-Compat"], include_in_schema=False)

from app.api.routes.analytics import router as analytics_router
app.include_router(analytics_router)

from app.api.routes.ai_feed import router as ai_feed_router
app.include_router(ai_feed_router, prefix="/api")

from app.api.routes.ai_intelligence import router as ai_intel_router
app.include_router(ai_intel_router)

from app.api.routes.ai_support import router as ai_support_router
app.include_router(ai_support_router)

from app.api.routes.basketball import router as basketball_router
app.include_router(basketball_router, prefix="/api")

from app.api.routes.tennis import router as tennis_router
app.include_router(tennis_router, prefix="/api")

from app.api.routes.watchlist import router as watchlist_router
app.include_router(watchlist_router, prefix="/api")

from app.api.routes.config import router as config_router
app.include_router(config_router, prefix="/api")

from app.api.routes.training import router as training_router
app.include_router(training_router, prefix="/api")

from app.api.routes.ai_assistant import router as ai_assistant_router
app.include_router(ai_assistant_router, prefix="/api")

from app.api.routes.admin import router as admin_router
app.include_router(admin_router, prefix="/api")

# --- Phase 0: Service Registry & Cross-Service Status ---
from app.api.routes.registry import router as registry_router
app.include_router(registry_router, prefix="/api", tags=["Registry"])

# --- Niche & Expansion Routers (from app/modules) ---
from app.modules.elections.routes import router as elections_router
app.include_router(elections_router, prefix="/api", tags=["Elections"])

from app.modules.policy.routes import router as policy_router
app.include_router(policy_router, prefix="/api", tags=["Policy"])

from app.modules.remittance.routes import router as remittance_router
app.include_router(remittance_router, prefix="/api", tags=["Remittance"])

from app.modules.merit.routes import router as merit_router
app.include_router(merit_router, prefix="/api", tags=["Merit"])

from app.modules.governance.routes import router as governance_router
app.include_router(governance_router, prefix="/api", tags=["Governance"])

from app.modules.academy.routes import router as academy_router
app.include_router(academy_router, prefix="/api", tags=["Academy"])

from app.modules.marketplace.routes import router as marketplace_router
app.include_router(marketplace_router, prefix="/api", tags=["Marketplace"])

from app.modules.referral.routes import router as referral_router
app.include_router(referral_router)

from app.api.routes.affiliate import router as affiliate_router
app.include_router(affiliate_router, prefix="/api")

from app.modules.notifications.routes import router as notifications_router
app.include_router(notifications_router)

from app.modules.developer.routes import router as developer_router
app.include_router(developer_router)

from app.modules.rewards.routes import router as rewards_router
app.include_router(rewards_router, prefix="/api", tags=["Rewards"])

from app.modules.did.routes import router as did_router
app.include_router(did_router, prefix="/api", tags=["DID"])

from app.modules.quant.routes import router as quant_router
app.include_router(quant_router, prefix="/api", tags=["Quant"])

# --- Phase VIII: DeFi, Social & Enterprise ---
from app.modules.social.routes import router as social_router
app.include_router(social_router, tags=["Social"])

from app.modules.defi.routes import router as defi_router
app.include_router(defi_router, tags=["DeFi"])

from app.modules.inplay.routes import router as inplay_router
app.include_router(inplay_router, tags=["In-Play"])

from app.modules.analytics_studio.routes import router as analytics_studio_router
app.include_router(analytics_studio_router, tags=["Analytics Studio"])

from app.modules.enterprise.routes import router as enterprise_router
app.include_router(enterprise_router, tags=["Enterprise"])

from app.modules.bridge.routes import router as bridge_router
app.include_router(bridge_router, prefix="/api", tags=["Bridge"])

from app.modules.treasury.routes import router as treasury_router
app.include_router(treasury_router, tags=["Treasury"])

# --- Wallet Routers ---
from app.modules.wallet.routes import router as wallet_router
app.include_router(wallet_router)

from app.modules.wallet.p2p_routes import router as p2p_router
app.include_router(p2p_router)

from app.modules.wallet.admin_routes import router as wallet_admin_router
app.include_router(wallet_admin_router)

# --- Notification & Websocket Routers (Mocked as missing) ---
@app.get("/api/notifications/status")
async def get_notification_status():
    return {"status": "active"}

@app.websocket("/api/notifications/ws")
async def notifications_websocket_endpoint(websocket):
    await websocket.accept()
    await websocket.send_json({"type": "pong"})
    await websocket.close()

@app.get("/api/system/kernel", tags=["System"])
async def get_kernel_status():
    return kernel.get_status()

@app.get("/api/system/registry", tags=["System"])
async def get_registry_diagnostics():
    from app.core.registry.manager import registry
    return registry.get_diagnostics()

@app.get("/api/system/health/summary", tags=["System"])
async def get_health_summary():
    # Read from obs_manager.health — this is the live source updated by the
    # kernel health-supervision loop.  The module registry health field is
    # never populated at runtime, so reading from it always shows UNKNOWN.
    from app.core.observability.manager import obs_manager as _obs
    from app.core.observability.models import HealthStatus as _HS
    statuses = _obs.health.get_all_statuses()
    summary = {"overall_status": "HEALTHY", "details": {}}
    unhealthy_count = 0
    for sub in statuses:
        summary["details"][sub.name] = sub.status.value
        if sub.status != _HS.HEALTHY:
            unhealthy_count += 1
    if unhealthy_count > 0:
        total = len(statuses)
        summary["overall_status"] = "DEGRADED" if unhealthy_count < total else "UNHEALTHY"
    return summary

if __name__ == "__main__":
    import uvicorn
    port = get_int_env("PORT", 8000)
    uvicorn.run(app, host="0.0.0.0", port=port)

# --- Static Files for Explorer ---
from fastapi.staticfiles import StaticFiles

explorer_path = "explorer/dist"
if os.path.exists(explorer_path):
    app.mount("/explorer", StaticFiles(directory=explorer_path, html=True), name="explorer")
