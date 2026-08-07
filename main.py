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
from app.modules.platform.routes import router as platform_events_router
from app.modules.platform.search_routes import router as platform_search_router

# --- VIT Runtime Kernel ---
# Wrapped in try/except: even a total import-chain failure must not cause
# nonZeroExit(1) before uvicorn binds, which would make /ping unreachable.
try:
    register_core_subsystems()
except Exception as _reg_exc:
    logging.getLogger(__name__).critical(
        "[main] register_core_subsystems() raised — kernel has NO subsystems: %s",
        _reg_exc, exc_info=True,
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_signal_handlers()

    async def _boot_and_setup() -> None:
        """
        Runs kernel.boot() and all post-boot setup in a background task.

        By doing this asynchronously, uvicorn can start serving /ping immediately
        so Render's health check passes before the DB/Redis subsystems are ready.
        Previously this ran synchronously before `yield`, blocking /ping for up to
        60+ seconds (asyncpg default timeout) and causing consistent update_failed.
        """
        try:
            await kernel.boot()
        except (KeyboardInterrupt, asyncio.CancelledError):
            return
        except BaseException as _boot_exc:
            logging.getLogger(__name__).critical(
                "[lifespan] kernel.boot() failed — service starting in DEGRADED state: %s",
                _boot_exc, exc_info=True,
            )

        # Phase 0: connect event bus Redis layer so events persist across restarts
        try:
            from app.core.event_bus import event_bus
            await event_bus.connect_redis()
        except Exception as _e:
            logging.getLogger(__name__).warning("[lifespan] event_bus.connect_redis failed: %s", _e)

        # TRACK-007: Start Agent Workflow Dispatcher
        try:
            from app.modules.agents.workflow import workflow_dispatcher
            await workflow_dispatcher.start()
            logging.getLogger(__name__).info("[lifespan] Agent Workflow Dispatcher started")
        except Exception as _we:
            logging.getLogger(__name__).warning("[lifespan] workflow dispatcher start failed: %s", _we)

        # TRACK-008: Start Tachyon Storage Challenge Scheduler
        try:
            from tachyon.core.challenge import challenge_scheduler
            await challenge_scheduler.start()
            logging.getLogger(__name__).info("[lifespan] Tachyon Challenge Scheduler started")
        except Exception as _ce:
            logging.getLogger(__name__).warning("[lifespan] challenge scheduler start failed: %s", _ce)

        # TRACK-008: Start Tachyon Verification Worker
        try:
            from tachyon.core.worker import TachyonVerificationWorker
            _tachyon_worker = TachyonVerificationWorker(interval_seconds=3600)
            asyncio.create_task(_tachyon_worker.start(), name="tachyon-verification-worker")
            logging.getLogger(__name__).info("[lifespan] Tachyon Verification Worker started")
        except Exception as _te:
            logging.getLogger(__name__).warning("[lifespan] tachyon verification worker failed: %s", _te)

        # TRACK-009: Start in-process APScheduler for autonomous agents (replaces Celery Beat)
        try:
            from app.core.swarm_orchestrator import get_swarm as _get_swarm
            _swarm = _get_swarm()
            _swarm.start_scheduler()
            logging.getLogger(__name__).info("[lifespan] SwarmOrchestrator APScheduler started (%d agents)", len(_swarm._agents))
        except Exception as _sch_e:
            logging.getLogger(__name__).warning("[lifespan] swarm scheduler start failed (agents will not auto-run): %s", _sch_e)

        logging.getLogger(__name__).info(
            "[lifespan] Background boot complete — VIT Network v%s fully operational.", APP_VERSION
        )

    # ── Background boot — /ping responds immediately ──────────────────────────
    # asyncio.create_task schedules the boot coroutine to run concurrently with
    # the server. The yield below happens right away, so Render's health check
    # gets a 200 from /ping even while subsystems are still initialising.
    _boot_task = asyncio.create_task(_boot_and_setup(), name="kernel-boot")

    print(f'🚀 VIT Network v{APP_VERSION} starting (RUNTIME KERNEL MODE)...')
    yield

    # ── Graceful shutdown ─────────────────────────────────────────────────────
    _boot_task.cancel()
    try:
        await _boot_task
    except asyncio.CancelledError:
        pass

    try:
        from app.modules.agents.workflow import workflow_dispatcher as _wd
        await _wd.stop()
    except Exception:
        pass
    try:
        from tachyon.core.challenge import challenge_scheduler as _cs
        await _cs.stop()
    except Exception:
        pass
    try:
        from app.core.swarm_orchestrator import get_swarm as _gs
        _gs().stop_scheduler()
    except Exception:
        pass
    try:
        from app.core.event_bus import event_bus as _eb
        await _eb.disconnect_redis()
    except Exception:
        pass

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

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return error_response(
        request=request,
        status_code=exc.status_code,
        code="http_error",
        message=str(exc.detail) if exc.detail else "HTTP error",
        details=None,
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
    # Do not expose version, environment, or internal subsystem names publicly
    return {
        "name": "VIT Platform",
        "status": "healthy",
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
async def readiness(request: Request, db: AsyncSession = Depends(get_db)):
    from fastapi.responses import JSONResponse
    db_ok = False
    redis_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    try:
        redis_client = getattr(request.app.state, "redis", None)
        if redis_client:
            await redis_client.ping()
            redis_ok = True
    except Exception:
        pass
    ready = db_ok  # DB is the hard requirement; Redis degraded is non-fatal
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "db": db_ok, "redis": redis_ok},
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
try:
    from app.auth.routes import router as auth_router
    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(auth_router, prefix="/auth", tags=["Auth-Compat"], include_in_schema=False)
except Exception as _e:
    logging.warning("auth_router not mounted — routes unavailable: %s", _e)

# Phase 3: Mount email verification and TOTP/2FA routers
try:
    from app.auth.verification import router as verification_router
    app.include_router(verification_router, prefix="/api", tags=["Auth — Verification"])
except Exception as _ve:
    logging.error("verification router not mounted — routes unavailable: %s", _ve, exc_info=True)
try:
    from app.auth.totp import router as totp_router
    app.include_router(totp_router, prefix="/api", tags=["Auth — 2FA"])
except Exception as _te:
    logging.error("totp router not mounted — routes unavailable: %s", _te, exc_info=True)

try:
    from app.api.routes.observability import router as obs_router
    app.include_router(obs_router, prefix="/api/obs", tags=["Observability"])
except Exception as _e:
    logging.warning("obs_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.identity.routes import router as identity_router
    app.include_router(identity_router, tags=["Identity"])
except Exception as _e:
    logging.warning("identity_router not mounted — routes unavailable: %s", _e)

try:
    from app.plugins.identity.routes import router as legacy_identity_router
    app.include_router(legacy_identity_router, prefix="/api/identity", tags=["Identity-Legacy"])
except Exception as _e:
    logging.warning("legacy_identity_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.identity_management import router as identity_mgmt_router
    app.include_router(identity_mgmt_router, tags=["Identity Management"])
except Exception as _e:
    logging.warning("identity_mgmt_router not mounted: %s", _e)

try:
    from app.api.routes.auth_extended import router as auth_extended_router
    app.include_router(auth_extended_router, prefix="/api", tags=["Auth — Extended"])
except Exception as _e:
    logging.warning("auth_extended_router not mounted: %s", _e)

try:
    from app.api.routes.blockchain import router as blockchain_router
    app.include_router(blockchain_router)
except Exception as _e:
    logging.warning("blockchain_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.blockchain.routes import router as blockchain_module_router
    app.include_router(blockchain_module_router)
except Exception as _e:
    logging.warning("blockchain_module_router not mounted — routes unavailable: %s", _e)

try:
    from vit_chain.rpc.router import router as chain_rpc_router
    app.include_router(chain_rpc_router)
except Exception as _e:
    logging.warning("chain_rpc_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.explorer import router as explorer_router
    app.include_router(explorer_router, prefix="/api")
except Exception as _e:
    logging.warning("explorer_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.blockchain_ws import router as blockchain_ws_router
    app.include_router(blockchain_ws_router)
except Exception as _e:
    logging.warning("blockchain_ws_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.blockchain_analytics import router as blockchain_analytics_router
    app.include_router(blockchain_analytics_router)
except Exception as _e:
    logging.warning("blockchain_analytics_router not mounted — routes unavailable: %s", _e)

# --- Business & AI Routers ---
try:
    from app.api.routes.matches import router as matches_router
    app.include_router(matches_router, prefix="/api")
except Exception as _e:
    logging.warning("matches_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.predict import router as predict_router
    app.include_router(predict_router, prefix="/api")
except Exception as _e:
    logging.warning("predict_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.attestation import router as attestation_router
    app.include_router(attestation_router)
except Exception as _e:
    logging.warning("attestation_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.payout_verify import router as payout_verify_router
    app.include_router(payout_verify_router)
except Exception as _e:
    logging.warning("payout_verify_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.multichain import router as multichain_router
    app.include_router(multichain_router, tags=["Multichain"])
except Exception as _e:
    logging.warning("multichain_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.dashboard import router as dashboard_router
    app.include_router(dashboard_router)
except Exception as _e:
    logging.warning("dashboard_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.sports import router as sports_router
    app.include_router(sports_router, prefix="/api")
except Exception as _sports_e:
    logging.error("sports router not mounted — sports endpoints unavailable: %s", _sports_e, exc_info=True)

try:
    from app.api.routes.analytics import router as analytics_router
    app.include_router(analytics_router)
except Exception as _e:
    logging.warning("analytics_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.ai_feed import router as ai_feed_router
    app.include_router(ai_feed_router, prefix="/api")
except Exception as _e:
    logging.warning("ai_feed_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.ai_intelligence import router as ai_intel_router
    app.include_router(ai_intel_router)
except Exception as _e:
    logging.warning("ai_intel_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.ai_support import router as ai_support_router
    app.include_router(ai_support_router)
except Exception as _e:
    logging.warning("ai_support_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.basketball import router as basketball_router
    app.include_router(basketball_router, prefix="/api")
except Exception as _e:
    logging.warning("basketball_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.tennis import router as tennis_router
    app.include_router(tennis_router, prefix="/api")
except Exception as _e:
    logging.warning("tennis_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.watchlist import router as watchlist_router
    app.include_router(watchlist_router, prefix="/api")
except Exception as _e:
    logging.warning("watchlist_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.config import router as config_router
    app.include_router(config_router, prefix="/api")
except Exception as _e:
    logging.warning("config_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.training import router as training_router
    app.include_router(training_router, prefix="/api")
except Exception as _e:
    logging.warning("training_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.ai_assistant import router as ai_assistant_router
    app.include_router(ai_assistant_router, prefix="/api")
except Exception as _e:
    logging.warning("ai_assistant_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.ai.routes import router as ai_module_router
    app.include_router(ai_module_router)
except Exception as _e:
    logging.warning("ai_module_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.admin import router as admin_router
    app.include_router(admin_router, prefix="/api")
    app.include_router(platform_events_router)
    app.include_router(platform_search_router)
except Exception as _e:
    logging.warning("admin_router not mounted — routes unavailable: %s", _e)

# Command Palette — Phase 1 feature; was missing from main.py despite the
# module and frontend component being fully implemented.
try:
    from app.modules.command_palette.routes import router as command_palette_router
    app.include_router(command_palette_router)
    logging.getLogger(__name__).info("[main] command_palette_router mounted at /api/platform/commands")
except Exception as _e:
    logging.warning("command_palette_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.admin_missing import router as admin_missing_router
    app.include_router(admin_missing_router, prefix="/api", tags=["Admin — Supplementary"])
except Exception as _e:
    logging.error("admin_missing router not mounted — routes unavailable: %s", _e, exc_info=True)

# --- Phase 0: Service Registry & Cross-Service Status ---
try:
    from app.api.routes.registry import router as registry_router
    app.include_router(registry_router, prefix="/api", tags=["Registry"])
except Exception as _e:
    logging.warning("registry_router not mounted — routes unavailable: %s", _e)
else:
    # Backwards-compatibility: some clients expect /registry and /status at root.
    # Expose lightweight proxy endpoints that call the same handlers but are
    # excluded from OpenAPI to avoid duplicate operation IDs.
    try:
        from app.api.routes.registry import get_registry as _get_registry, get_platform_status as _get_platform_status
        app.add_api_route("/registry", _get_registry, methods=["GET"], include_in_schema=False)
        app.add_api_route("/status", _get_platform_status, methods=["GET"], include_in_schema=False)
    except Exception as _e:
        logging.warning("Failed to add registry compatibility routes: %s", _e)

# --- Niche & Expansion Routers (from app/modules) ---
try:
    from app.modules.elections.routes import router as elections_router
    app.include_router(elections_router, prefix="/api", tags=["Elections"])
except Exception as _e:
    logging.warning("elections_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.policy.routes import router as policy_router
    app.include_router(policy_router, prefix="/api", tags=["Policy"])
except Exception as _e:
    logging.warning("policy_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.remittance.routes import router as remittance_router
    app.include_router(remittance_router, prefix="/api", tags=["Remittance"])
except Exception as _e:
    logging.warning("remittance_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.merit.routes import router as merit_router
    app.include_router(merit_router, tags=["Merit"])  # router self-prefixes /api/merit
except Exception as _e:
    logging.warning("merit_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.governance.routes import router as governance_router
    app.include_router(governance_router, tags=["Governance"])  # router self-prefixes /api/governance
except Exception as _e:
    logging.warning("governance_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.academy.routes import router as academy_router
    app.include_router(academy_router, tags=["Academy"])  # router self-prefixes /api/academy
except Exception as _e:
    logging.warning("academy_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.marketplace.routes import router as marketplace_router
    app.include_router(marketplace_router, tags=["Marketplace"])  # router self-prefixes /api/marketplace
except Exception as _e:
    logging.warning("marketplace_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.referral.routes import router as referral_router
    app.include_router(referral_router)
except Exception as _e:
    logging.warning("referral_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.affiliate import router as affiliate_router
    app.include_router(affiliate_router, prefix="/api")
except Exception as _e:
    logging.warning("affiliate_router not mounted — routes unavailable: %s", _e)

try:
    from app.api.routes.predictions_compat import router as predictions_compat_router
    app.include_router(predictions_compat_router, prefix="/api")
except Exception as _e:
    logging.warning("predictions_compat_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.notifications.routes import router as notifications_router
    app.include_router(notifications_router)
except Exception as _e:
    logging.warning("notifications_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.developer.routes import router as developer_router
    app.include_router(developer_router)
except Exception as _e:
    logging.warning("developer_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.rewards.routes import router as rewards_router
    app.include_router(rewards_router, tags=["Rewards"])  # router self-prefixes /api/rewards
except Exception as _e:
    logging.warning("rewards_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.did.routes import router as did_router
    app.include_router(did_router, tags=["DID"])  # router self-prefixes /api/did
except Exception as _e:
    logging.warning("did_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.quant.routes import router as quant_router
    app.include_router(quant_router, tags=["Quant"])  # router self-prefixes /api/quant
except Exception as _e:
    logging.warning("quant_router not mounted — routes unavailable: %s", _e)

# --- Phase VIII: DeFi, Social & Enterprise ---
try:
    from app.modules.social.routes import router as social_router
    app.include_router(social_router, tags=["Social"])
except Exception as _e:
    logging.warning("social_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.defi.routes import router as defi_router
    app.include_router(defi_router, tags=["DeFi"])
except Exception as _e:
    logging.warning("defi_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.inplay.routes import router as inplay_router
    app.include_router(inplay_router, tags=["In-Play"])
except Exception as _e:
    logging.warning("inplay_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.analytics_studio.routes import router as analytics_studio_router
    app.include_router(analytics_studio_router, tags=["Analytics Studio"])
except Exception as _e:
    logging.warning("analytics_studio_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.enterprise.routes import router as enterprise_router
    app.include_router(enterprise_router, tags=["Enterprise"])
except Exception as _e:
    logging.warning("enterprise_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.bridge.routes import router as bridge_router
    app.include_router(bridge_router, tags=["Bridge"])  # router self-prefixes /api/bridge
except Exception as _e:
    logging.warning("bridge_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.treasury.routes import router as treasury_router
    app.include_router(treasury_router, tags=["Treasury"])
except Exception as _e:
    logging.warning("treasury_router not mounted — routes unavailable: %s", _e)

# --- Wallet Routers ---
try:
    from app.modules.wallet.routes import router as wallet_router
    app.include_router(wallet_router)
except Exception as _e:
    logging.warning("wallet_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.wallet.p2p_routes import router as p2p_router
    # p2p_router has prefix="/wallet/p2p"; mount with /api to produce /api/wallet/p2p/...
    app.include_router(p2p_router, prefix="/api")
except Exception as _e:
    logging.warning("p2p_router not mounted — routes unavailable: %s", _e)

try:
    from app.modules.wallet.admin_routes import router as wallet_admin_router
    app.include_router(wallet_admin_router)
except Exception as _e:
    logging.warning("wallet_admin_router not mounted — routes unavailable: %s", _e)

# --- Previously unmounted API route routers (Phase-2 mount) ---
try:
    from app.api.routes.audit import router as audit_router
    app.include_router(audit_router, prefix="/api", tags=["Audit"])
except Exception as _e:
    logging.error("audit router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.history import router as history_router
    app.include_router(history_router, prefix="/api", tags=["History"])
except Exception as _e:
    logging.error("history router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.leaderboard import router as leaderboard_router
    app.include_router(leaderboard_router, tags=["Leaderboard"])
except Exception as _e:
    logging.error("leaderboard router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.result import router as result_router
    app.include_router(result_router, prefix="/api", tags=["Results"])
except Exception as _e:
    logging.error("result router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.rollover import router as rollover_router
    app.include_router(rollover_router, prefix="/api", tags=["Rollover"])
except Exception as _e:
    logging.error("rollover router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.exports import router as exports_router
    app.include_router(exports_router, tags=["Exports"])
except Exception as _e:
    logging.error("exports router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.subscription import router as subscription_router
    app.include_router(subscription_router, prefix="/api", tags=["Subscription"])
except Exception as _e:
    logging.error("subscription router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.similarity import router as similarity_router
    app.include_router(similarity_router, tags=["Similarity"])
except Exception as _e:
    logging.error("similarity router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.quality_feed import router as quality_feed_router
    app.include_router(quality_feed_router, prefix="/api", tags=["Quality Feed"])
except Exception as _e:
    logging.error("quality_feed router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.agents import router as agents_router
    app.include_router(agents_router, prefix="/api", tags=["Agents"])
except Exception as _e:
    logging.error("agents router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.agent_status import router as agent_status_router
    app.include_router(agent_status_router, prefix="/api", tags=["Agent Status"])
except Exception as _e:
    logging.error("agent_status router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.ai import router as ai_mgmt_router
    app.include_router(ai_mgmt_router, prefix="/api", tags=["AI Management"])
except Exception as _e:
    logging.error("ai management router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.bankroll import router as bankroll_router
    app.include_router(bankroll_router, tags=["Bankroll"])
except Exception as _e:
    logging.error("bankroll router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.odds_compare import router as odds_compare_router
    app.include_router(odds_compare_router, prefix="/api", tags=["Odds Compare"])
except Exception as _e:
    logging.error("odds_compare router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.market_training import router as market_training_router
    app.include_router(market_training_router, tags=["Market Training"])
except Exception as _e:
    logging.error("market_training router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.model_breakdown import router as model_breakdown_router
    app.include_router(model_breakdown_router, prefix="/api", tags=["Model Breakdown"])
except Exception as _e:
    logging.error("model_breakdown router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.model_performance import router as model_performance_router
    app.include_router(model_performance_router, prefix="/api", tags=["Model Performance"])
except Exception as _e:
    logging.error("model_performance router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.cloud_status import router as cloud_status_router
    app.include_router(cloud_status_router, prefix="/api", tags=["Cloud Status"])
except Exception as _e:
    logging.error("cloud_status router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.storage_nodes import router as storage_nodes_router
    app.include_router(storage_nodes_router, tags=["Storage Nodes"])
except Exception as _e:
    logging.error("storage_nodes router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.postbacks import router as postbacks_router
    app.include_router(postbacks_router, tags=["Postbacks"])
except Exception as _e:
    logging.error("postbacks router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.sports_webhooks import router as sports_webhooks_router
    app.include_router(sports_webhooks_router, prefix="/api", tags=["Sports Webhooks"])
except Exception as _e:
    logging.error("sports_webhooks router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.paystack_webhooks import router as paystack_webhooks_router
    app.include_router(paystack_webhooks_router, prefix="/api", tags=["Paystack Webhooks"])
except Exception as _e:
    logging.error("paystack_webhooks router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.wrapped import router as wrapped_router
    app.include_router(wrapped_router, prefix="/api", tags=["Wrapped"])
except Exception as _e:
    logging.error("wrapped router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.admin_audit_predictions import router as admin_audit_pred_router
    app.include_router(admin_audit_pred_router, prefix="/api", tags=["Admin Audit"])
except Exception as _e:
    logging.error("admin_audit_predictions router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.admin_rewards import router as admin_rewards_router
    app.include_router(admin_rewards_router, prefix="/api", tags=["Admin Rewards"])
except Exception as _e:
    logging.error("admin_rewards router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.admin_tasks import router as admin_tasks_router
    app.include_router(admin_tasks_router, prefix="/api", tags=["Admin Tasks"])
except Exception as _e:
    logging.error("admin_tasks router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.admin_clv import router as admin_clv_router
    app.include_router(admin_clv_router, prefix="/api", tags=["Admin CLV"])
except Exception as _e:
    logging.error("admin_clv router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.admin_finance import router as admin_finance_router
    app.include_router(admin_finance_router, prefix="/api", tags=["Admin Finance"])
except Exception as _e:
    logging.error("admin_finance router not mounted — routes unavailable: %s", _e, exc_info=True)

try:
    from app.api.routes.admin_ops import router as admin_ops_router
    app.include_router(admin_ops_router, prefix="/api", tags=["Admin Ops"])
except Exception as _e:
    logging.error("admin_ops router not mounted — routes unavailable: %s", _e, exc_info=True)

# ---------------------------------------------------------------------------
# Phase 4-5 Gap Resolution — mount remaining module routers
# All wrapped in try/except so a broken import never kills the whole process
# ---------------------------------------------------------------------------

# AI Verification — anchor proofs, verify, dispute (/api/ai-verify/*)
try:
    from app.modules.ai_verification.routes import router as ai_verify_router
    app.include_router(ai_verify_router, tags=["AI Verification"])
except Exception as _e:
    logging.error("ai_verification router not mounted: %s", _e, exc_info=True)

# Trust & Reputation — anti-fraud, reputation scoring (/api/trust/*)
try:
    from app.modules.trust.routes import router as trust_router
    app.include_router(trust_router, tags=["Trust"])
except Exception as _e:
    logging.error("trust router not mounted: %s", _e, exc_info=True)

# Community Circles (/api/community/*)
try:
    from app.modules.community.routes import router as community_router
    app.include_router(community_router, prefix="/api", tags=["Community"])
except Exception as _e:
    logging.error("community router not mounted: %s", _e, exc_info=True)

# Task System — module-level task queue (/api/tasks/*)
try:
    from app.modules.tasks.routes import router as tasks_module_router
    app.include_router(tasks_module_router, tags=["Tasks"])
except Exception as _e:
    logging.error("tasks module router not mounted: %s", _e, exc_info=True)

# Freemium — IQ Test & Oracle Mic (/api/freemium/*)
try:
    from app.modules.freemium.routes import router as freemium_router
    app.include_router(freemium_router, tags=["Freemium"])
except Exception as _e:
    logging.error("freemium router not mounted: %s", _e, exc_info=True)

# Security — anti-Sybil, fraud alerts, multi-sig, wallet freeze (/api/security/*)
try:
    from app.modules.security.routes import router as security_router
    app.include_router(security_router, tags=["Security"])
except Exception as _e:
    logging.error("security router not mounted: %s", _e, exc_info=True)

# Storage Verification — Tachyon VESS content registry & proofs (/api/storage/*)
try:
    from app.modules.storage_verification.routes import router as storage_verify_router
    app.include_router(storage_verify_router, tags=["Storage Verification"])
except Exception as _e:
    logging.error("storage_verification router not mounted: %s", _e, exc_info=True)

# KYC Engine — offline verification, risk scoring (/api/kyc/*)
try:
    from app.modules.kyc.routes import router as kyc_router
    app.include_router(kyc_router, tags=["KYC"])
except Exception as _e:
    logging.error("kyc router not mounted: %s", _e, exc_info=True)

# Smart Contracts — deploy, call, query, upgrade (/api/contracts/*)
try:
    from app.modules.smart_contracts.routes import router as smart_contracts_router
    app.include_router(smart_contracts_router, tags=["Smart Contracts"])
except Exception as _e:
    logging.error("smart_contracts router not mounted: %s", _e, exc_info=True)

# Sub-Chain Registry — chain registry & cross-chain messaging (/api/subchains/*)
try:
    from app.modules.subchain.routes import router as subchain_router
    app.include_router(subchain_router, tags=["Sub-Chain"])
except Exception as _e:
    logging.error("subchain router not mounted: %s", _e, exc_info=True)

# AI Core — Atomic Match Model, Player DNA, Causal Inference (/api/ai-core/*)
try:
    from app.modules.ai_core.routes import router as ai_core_router
    app.include_router(ai_core_router, tags=["AI Core"])
except Exception as _e:
    logging.error("ai_core router not mounted: %s", _e, exc_info=True)

# Merchant Services — onboarding & business profiles (/api/merchant/*)
try:
    from app.modules.marketplace.merchant import router as merchant_router
    app.include_router(merchant_router, tags=["Merchant"])
except Exception as _e:
    logging.error("merchant router not mounted: %s", _e, exc_info=True)

# Agent Registry — register, manage & track AI agents (/api/agents/registry/*)
try:
    from app.modules.agent_registry.routes import router as agent_registry_router
    app.include_router(agent_registry_router, tags=["Agent Registry"])
except Exception as _e:
    logging.error("agent_registry router not mounted: %s", _e, exc_info=True)

# Prophecy Chain — prediction anchoring (/prophecy/*)
try:
    from app.modules.prophecy_chain.routes import router as prophecy_chain_router
    app.include_router(prophecy_chain_router, tags=["Prophecy Chain"])
except Exception as _e:
    logging.error("prophecy_chain router not mounted: %s", _e, exc_info=True)

# Network — VIT P2P node registry & stats (/api/network/*)
try:
    from app.modules.network.routes import router as network_router
    app.include_router(network_router, tags=["Network"])
except Exception as _e:
    logging.error("network router not mounted: %s", _e, exc_info=True)

# Network — Campus Node Registry (/api/network/campus/*)
try:
    from app.modules.network.campus_node import router as campus_node_router
    app.include_router(campus_node_router, tags=["Campus Nodes"])
except Exception as _e:
    logging.error("campus_node router not mounted: %s", _e, exc_info=True)

# Network — University Nodes (/api/network/universities/*)
try:
    from app.modules.network.university_api import router as university_api_router
    app.include_router(university_api_router, tags=["Universities"])
except Exception as _e:
    logging.error("university_api router not mounted: %s", _e, exc_info=True)

# Network — Android (Mobile) Nodes (/api/network/android/*)
try:
    from app.modules.network.android_node import router as android_node_router
    app.include_router(android_node_router, tags=["Android Nodes"])
except Exception as _e:
    logging.error("android_node router not mounted: %s", _e, exc_info=True)

# Academy — Campus Hub overview (/api/campus/*)
try:
    from app.modules.academy.campus import router as campus_hub_router
    app.include_router(campus_hub_router, tags=["Campus Hub"])
except Exception as _e:
    logging.error("campus hub router not mounted: %s", _e, exc_info=True)

# Academy — Campus Circles (Communities) (/api/campus/circles/*)
try:
    from app.modules.academy.communities import router as campus_circles_router
    app.include_router(campus_circles_router, tags=["Campus Circles"])
except Exception as _e:
    logging.error("campus_circles router not mounted: %s", _e, exc_info=True)

# Academy — Campus Gigs (Micro-tasks) (/api/campus/gigs/*)
try:
    from app.modules.academy.gigs import router as campus_gigs_router
    app.include_router(campus_gigs_router, tags=["Campus Gigs"])
except Exception as _e:
    logging.error("campus_gigs router not mounted: %s", _e, exc_info=True)

# Wallet — Payment Webhooks (Paystack, Flutterwave, USDT) (/api/webhooks/*)
try:
    from app.modules.wallet.webhooks import router as wallet_webhooks_router
    app.include_router(wallet_webhooks_router, tags=["Wallet Webhooks"])
except Exception as _e:
    logging.error("wallet_webhooks router not mounted: %s", _e, exc_info=True)

# Wallet — Direct VITCoin Sale (/api/wallet/vitcoin/*)
try:
    from app.modules.wallet.direct_sale import router as direct_sale_router
    app.include_router(direct_sale_router, prefix="/api", tags=["Direct Sale"])
except Exception as _e:
    logging.error("direct_sale router not mounted: %s", _e, exc_info=True)

# Wallet — On-Chain Transfer & Bridge (/api/wallet/bridge/*)
try:
    from app.modules.wallet.on_chain_transfer import router as on_chain_transfer_router
    app.include_router(on_chain_transfer_router, prefix="/api", tags=["Chain Bridge"])
except Exception as _e:
    logging.error("on_chain_transfer router not mounted: %s", _e, exc_info=True)

# Wallet — Real-Time Price WebSocket (/ws/wallet/price)
try:
    from app.modules.wallet.ws_price import router as ws_price_router
    app.include_router(ws_price_router, tags=["Wallet WebSocket"])
except Exception as _e:
    logging.error("ws_price router not mounted: %s", _e, exc_info=True)

# Blockchain Oracle — match result consensus (/api/oracle/*)
try:
    from app.modules.blockchain.oracle import router as oracle_router
    app.include_router(oracle_router, tags=["Oracle"])
except Exception as _e:
    logging.error("oracle router not mounted: %s", _e, exc_info=True)

# Tachyon VESS — Distributed Storage API (/api/tachyon/*)
try:
    from tachyon.api.router import router as tachyon_router
    app.include_router(tachyon_router, prefix="/api/tachyon", tags=["Tachyon"])
except Exception as _e:
    logging.error("tachyon router not mounted: %s", _e, exc_info=True)

# Tachyon VESS — Admin (/api/tachyon/admin/*)
try:
    from tachyon.api.admin_routes import router as tachyon_admin_router
    app.include_router(tachyon_admin_router, prefix="/api/tachyon/admin", tags=["Tachyon Admin"])
except Exception as _e:
    logging.error("tachyon_admin router not mounted: %s", _e, exc_info=True)

# TRACK-009: Global Search (/api/search)
try:
    from app.api.routes.search import router as global_search_router
    app.include_router(global_search_router, tags=["Global Search"])
except Exception as _e:
    logging.error("global_search router not mounted: %s", _e, exc_info=True)

# TRACK-007: Agent Workflow Manager (/api/agents/workflow)
try:
    from app.api.routes.agent_workflow import router as agent_workflow_router
    app.include_router(agent_workflow_router, tags=["Agent Workflow"])
except Exception as _e:
    logging.error("agent_workflow router not mounted: %s", _e, exc_info=True)

# TRACK-008: Tachyon Storage Challenges (/api/tachyon/challenges)
try:
    from app.api.routes.tachyon_challenges import router as tachyon_challenges_router
    app.include_router(tachyon_challenges_router, tags=["Tachyon Challenges"])
except Exception as _e:
    logging.error("tachyon_challenges router not mounted: %s", _e, exc_info=True)

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

# --- React SPA (main frontend) ---
# Serve frontend/dist as a SPA. Assets (JS/CSS) are served directly;
# all other non-API paths fall through to index.html so React Router handles them.
from fastapi.responses import FileResponse

_frontend_dist = "frontend/dist"

if os.path.exists(_frontend_dist):
    # Serve static assets (JS, CSS, images, etc.) with long immutable cache headers.
    # Vite generates content-hashed filenames so these can be cached indefinitely.
    @app.get("/assets/{asset_path:path}", include_in_schema=False)
    async def serve_asset(asset_path: str):
        full = os.path.join(_frontend_dist, "assets", asset_path)
        if not os.path.exists(full) or not os.path.isfile(full):
            raise HTTPException(status_code=404)
        return FileResponse(
            full,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        _f = f"{_frontend_dist}/favicon.ico"
        if os.path.exists(_f):
            return FileResponse(_f)
        raise HTTPException(status_code=404)

    @app.get("/logo.png", include_in_schema=False)
    async def logo():
        _f = f"{_frontend_dist}/logo.png"
        if os.path.exists(_f):
            return FileResponse(_f)
        raise HTTPException(status_code=404)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Catch-all: serve index.html so React Router handles client-side navigation.
        Skips paths that already matched API routes above this mount point.
        """
        # Don't serve SPA for API / websocket routes (they already have handlers above)
        if full_path.startswith(("api/", "ws/", "ping", "health", "system/")):
            raise HTTPException(status_code=404)
        index = f"{_frontend_dist}/index.html"
        # index.html must never be cached: browsers would serve a stale bundle
        # after deployment, causing 405 / stale-asset errors until hard refresh.
        return FileResponse(
            index,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @app.api_route(
        "/{full_path:path}",
        methods=["POST", "PUT", "PATCH", "DELETE"],
        include_in_schema=False,
    )
    async def catch_unregistered_api_methods(full_path: str):
        """Guard against FastAPI's automatic 405 escalation.

        The SPA GET catch-all above registers GET /{full_path:path}.  When any other
        HTTP method (POST, PUT, PATCH, DELETE) arrives for a path with no dedicated
        handler, FastAPI would normally return 405 Method Not Allowed because it sees
        the matching GET route.  That was the root cause of the login 405 bug — a
        frontend typo sent POST /api/auth/auth/login, which only the SPA GET handler
        matched, producing 405 instead of a clear 404.

        This explicit catch-all returns a consistent 404 for all unregistered write-method
        requests so callers see a meaningful "not found" rather than the misleading
        "method not allowed".
        """
        raise HTTPException(status_code=404, detail="Not Found")
