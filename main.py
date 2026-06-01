# main.py — VIT Sports Intelligence Network v5.2.0
# Full Integration: Native AI + Wallet + Blockchain + Training

import asyncio
import logging
import os
import time
import uuid
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func

from fastapi.middleware.gzip import GZipMiddleware
from app.config import get_env, APP_VERSION, print_config_status, ADMIN_EMAIL, ADMIN_USERNAME, ADMIN_PASSWORD
from app.core.errors import AppError, error_response
from app.db.database import get_db
import app.db.models
import app.modules.wallet.models
import app.modules.blockchain.models
import app.modules.training.models
import app.modules.ai.models
import app.data.models
import app.modules.notifications.models
import app.modules.marketplace.models
import app.modules.trust.models
import app.modules.rewards.models
import app.modules.bridge.models
import app.modules.developer.models
import app.modules.governance.models
import app.modules.referral.models
import app.modules.tasks.models
import app.modules.did.models
import app.modules.network.models
import app.modules.smart_contracts.models
import app.modules.treasury.models
import app.modules.merit.models
import app.modules.ai_verification.models
import app.modules.security.models
import app.modules.subchain.models
import app.modules.agent_registry.models
import app.modules.storage_verification.models
import app.modules.prophecy_chain.models
import app.modules.academy.models
import app.modules.ai_core.models
import app.modules.quant.models

# ===== CORE ROUTES =====
from app.api.routes import (
    predict, result, history, admin, ai_feed, ai as ai_route,
    config as config_route, training as training_route, analytics as analytics_route,
    odds_compare as odds_route, subscription as subscription_route,
    audit as audit_route, matches as matches_route, ai_assistant as ai_assistant_route,
    ai_intelligence as ai_intelligence_route, ai_support as ai_support_route
)

from app.auth.routes import router as auth_router
from app.modules.wallet.routes import router as wallet_router
from app.modules.wallet.admin_routes import router as wallet_admin_router
from app.modules.wallet.webhooks import router as webhooks_router
from app.modules.blockchain.routes import router as blockchain_router
from app.modules.blockchain.oracle import router as oracle_router
from app.modules.training.routes import router as training_module_router
from app.modules.ai.routes import router as ai_engine_router
from app.api.routes.dashboard import router as dashboard_router
from app.data.routes import router as pipeline_router
from app.modules.notifications.routes import router as notifications_router
from app.modules.notifications.websocket import router as notifications_ws_router
from app.modules.tasks.routes import router as tasks_router
from app.api.routes.postbacks import router as postbacks_router
from app.api.routes.admin_rewards import router as admin_rewards_router
from app.modules.rewards.routes import router as rewards_router
from app.modules.marketplace.routes import router as marketplace_router
from app.modules.trust.routes import router as trust_router
from app.modules.bridge.routes import router as bridge_router
from app.modules.developer.routes import router as developer_router
from app.modules.governance.routes import router as governance_router
from app.auth.verification import router as verification_router
from app.auth.totp import router as totp_router
from app.modules.elections.routes import router as elections_router
from app.modules.policy.routes import router as policy_router
from app.modules.remittance.routes import router as remittance_router
from app.api.routes.basketball import router as basketball_router
from app.api.routes.tennis import router as tennis_router
from app.modules.referral.routes import router as referral_router
from app.api.routes.leaderboard import router as leaderboard_router
from app.api.routes.exports import router as exports_router
from app.api.routes.admin_ai_sources import router as admin_ai_sources_router
from app.api.routes.model_breakdown import router as model_breakdown_router
from app.api.routes.admin_clv import router as admin_clv_router
from app.api.routes.agents import router as agents_router
from app.modules.did.routes import router as did_router
import app.modules.identity.models
from app.modules.identity.routes import router as identity_router
import app.modules.kyc.models
from app.modules.kyc.routes import router as kyc_router
from app.modules.network.routes import router as network_router
from app.iot.router import router as iot_router
from app.agents.coordinator import AgentCoordinator

# ===== MIDDLEWARE =====
from app.api.middleware.auth import APIKeyMiddleware
from app.api.middleware.logging import LoggingMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.middleware.security import SecurityHeadersMiddleware
from app.api.middleware.request_id import RequestIDMiddleware

# ===== SERVICES =====
from app.schemas.schemas import HealthResponse
from app.services.alerts import TelegramAlert
from app.core.dependencies import (
    get_orchestrator,
    get_data_loader,
    get_telegram_alerts,
)

load_dotenv()
logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.logging_config import configure_logging
    configure_logging(level=get_env("LOG_LEVEL", "INFO"))
    print_config_status()
    print(f"🚀 VIT Network v{APP_VERSION} starting (NATIVE AI MODE)...")
    _bootstrap_task = asyncio.create_task(_run_bootstrap(app, None), name="bootstrap")
    yield
    if not _bootstrap_task.done():
        _bootstrap_task.cancel()
    print("🛑 Shutdown complete")

async def _run_bootstrap(app, _done_event):
    try:
        from app.db.database import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            from app.modules.ai.models import AIInsight
            from app.modules.wallet.models import PlatformConfig
            await conn.run_sync(AIInsight.__table__.create, checkfirst=True)
            await conn.run_sync(PlatformConfig.__table__.create, checkfirst=True)
        print("✅ Database: all tables verified")

        from app.core.secrets_loader import load_all_secrets
        await load_all_secrets()

    except Exception as e:
        print(f"❌ Bootstrap failed: {e}")

app = FastAPI(
    title="Value Intelligence Trust (VIT)",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(APIKeyMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestIDMiddleware)

# Error handlers
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return error_response(request=request, status_code=exc.status_code, code=exc.code, message=exc.message, details=exc.details)

@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    return error_response(request=request, status_code=exc.status_code, code="http_error", message=str(exc.detail))

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return error_response(request=request, status_code=422, code="validation_error", message="Request validation failed", details=exc.errors())

# Core
app.include_router(predict.router, prefix="/api")
app.include_router(result.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(matches_route.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(ai_route.router, prefix="/api")
app.include_router(ai_assistant_route.router, prefix="/api")
app.include_router(ai_intelligence_route.router, prefix="/api")
app.include_router(ai_support_route.router, prefix="/api")
app.include_router(auth_router)
app.include_router(wallet_router)
app.include_router(marketplace_router)
app.include_router(blockchain_router)
app.include_router(oracle_router)
app.include_router(training_module_router)
app.include_router(ai_engine_router)
app.include_router(dashboard_router)
app.include_router(pipeline_router)
app.include_router(notifications_router)
app.include_router(notifications_ws_router)
app.include_router(tasks_router)
app.include_router(postbacks_router)
app.include_router(admin_rewards_router, prefix="/api")
app.include_router(rewards_router)
app.include_router(trust_router)
app.include_router(bridge_router)
app.include_router(developer_router)
app.include_router(governance_router)
app.include_router(verification_router)
app.include_router(totp_router)
app.include_router(referral_router)
app.include_router(leaderboard_router)
app.include_router(exports_router)
app.include_router(agents_router, prefix="/api")
app.include_router(iot_router, prefix="/api")
app.include_router(did_router)
app.include_router(identity_router)
app.include_router(kyc_router)
app.include_router(network_router)

@app.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)):
    from app.services.ai_client import provider_status
    status = await provider_status()
    return {
        "status": "ok",
        "version": APP_VERSION,
        "models_loaded": status["native"]["models_ready"],
        "db_connected": True,
        "clv_tracking_enabled": True
    }

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
    file_path = os.path.join(dist, full_path)
    if os.path.isfile(file_path): return FileResponse(file_path)
    return FileResponse(os.path.join(dist, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
