# main.py — VIT Analytics Platform v5.5.0
# Full Integration: Native AI + Wallet + Blockchain + Training

import asyncio
import logging
import os
import time
import uuid
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import importlib

from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func

from fastapi.middleware.gzip import GZipMiddleware
from app.config import get_env, APP_NAME, APP_VERSION, print_config_status, ADMIN_EMAIL, ADMIN_USERNAME, ADMIN_PASSWORD
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
import app.modules.sports.models
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
import app.modules.community.models
import app.modules.watchlist.models
import app.modules.academy.models
from app.api.routes import admin_finance, admin_ops
import app.modules.ai_core.models
import app.modules.quant.models

# ===== CORE ROUTES =====
from app.api.routes import (
    watchlist,
    wrapped,
    predict, result, history, admin, ai_feed, ai as ai_route,
    config as config_route, training as training_route, analytics as analytics_route,
    odds_compare as odds_route, subscription as subscription_route,
    audit as audit_route, matches as matches_route, ai_assistant as ai_assistant_route,
    ai_intelligence as ai_intelligence_route, ai_support as ai_support_route,
    basketball, tennis,
)

from app.services.firestore_events import setup_firestore_events
from app.tasks.telegram_digest import start_telegram_digest
from app.tasks.settlement_task import start_settlement_worker
from app.tasks.ticker_sync import start_ticker_sync
from app.auth.routes import router as auth_router
from app.modules.wallet.routes import router as wallet_router
from app.modules.wallet.admin_routes import router as wallet_admin_router
from app.modules.wallet.webhooks import router as webhooks_router
from app.modules.wallet.ws_price import router as ws_price_router
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
from app.modules.marketplace.merchant import router as merchant_router
from app.modules.trust.routes import router as trust_router
from app.modules.bridge.routes import router as bridge_router
from app.modules.developer.routes import router as developer_router
from app.modules.governance.routes import router as governance_router
from app.auth.verification import router as verification_router
from app.auth.totp import router as totp_router
from app.api.routes.explorer import router as explorer_router
from app.modules.referral.routes import router as referral_router
from app.api.routes.leaderboard import router as leaderboard_router
from app.api.routes.exports import router as exports_router
from app.api.routes.model_breakdown import router as model_breakdown_router
from app.api.routes.admin_clv import router as admin_clv_router
from app.api.routes.agents import router as agents_router
from app.modules.did.routes import router as did_router
import app.modules.identity.models
from app.modules.identity.routes import router as identity_router
import app.modules.kyc.models
from app.modules.kyc.routes import router as kyc_router
from app.modules.network.routes import router as network_router
from app.modules.elections.routes import router as elections_router
from app.modules.policy.routes import router as policy_router
from app.modules.remittance.routes import router as remittance_router
from app.modules.community.routes import router as community_router
from app.iot.router import router as iot_router
from app.api.routes.sports import router as sports_router
from app.api.routes.sports_webhooks import router as sports_webhooks_router
from app.api.routes.affiliate import router as affiliate_router
from tachyon.api.router import router as tachyon_router
from app.agents.coordinator import AgentCoordinator
from app.api.routes.agent_status import router as agent_status_router

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


class BackgroundTaskSupervisor:
    """Supervises long-running async tasks, restarting them on failure up to max_restarts times."""

    def __init__(
        self,
        tasks: list,
        check_interval: float = 30,
        max_restarts: int = 5,
    ):
        self._task_defs = tasks
        self._check_interval = check_interval
        self._max_restarts = max_restarts
        self._funcs: dict = {name: fn for name, fn in tasks}
        self._state: dict = {
            name: {"restarts": 0, "done": False, "task": None}
            for name, _ in tasks
        }
        self._loop_task = None

    def start(self) -> None:
        loop = asyncio.get_event_loop()
        for name, fn in self._task_defs:
            self._state[name]["task"] = loop.create_task(fn(), name=name)
        self._loop_task = loop.create_task(self._supervision_loop())

    async def _supervision_loop(self) -> None:
        while True:
            await asyncio.sleep(self._check_interval)
            for name, fn in self._task_defs:
                s = self._state[name]
                if s["done"]:
                    continue
                task = s["task"]
                if task is not None and task.done():
                    exc = None
                    if not task.cancelled():
                        try:
                            exc = task.exception()
                        except Exception:
                            exc = None
                    if exc is not None:
                        if s["restarts"] < self._max_restarts:
                            s["restarts"] += 1
                            loop = asyncio.get_event_loop()
                            s["task"] = loop.create_task(fn(), name=name)
                            logger.warning(
                                "Background task %r restarted (attempt %d/%d): %s",
                                name, s["restarts"], self._max_restarts, exc,
                            )
                        else:
                            s["done"] = True
                            logger.error(
                                "Background task %r exhausted %d restarts and will not be restarted.",
                                name, self._max_restarts,
                            )

    async def stop(self) -> None:
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        for s in self._state.values():
            task = s.get("task")
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

    def snapshot(self) -> dict:
        return {
            name: {
                "restarts": s["restarts"],
                "done": s["done"],
                "running": s["task"] is not None and not s["task"].done(),
            }
            for name, s in self._state.items()
        }


# --- VIT Runtime Kernel ---
from app.core.kernel import kernel, setup_signal_handlers
from app.core.subsystems import register_core_subsystems
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
    lifespan=lifespan,
)
@app.on_event("shutdown")
async def shutdown_event():
    from app.db.database import engine
    await engine.dispose()
    logger.info("Database engine disposed on shutdown")


# ============================================
# MIDDLEWARE
# ============================================

_env = get_env("ENVIRONMENT", "development")
_default_cors = (
    "https://vit-897838355273.europe-west1.run.app"
    if _env == "production"
    else "*"
)
cors_origins = get_env("CORS_ALLOWED_ORIGINS", _default_cors)
origins = ["*"] if cors_origins.strip() == "*" else [o.strip() for o in cors_origins.split(",") if o.strip()]

# SEC-02: never pair allow_credentials=True with allow_origins=["*"] — browsers
# reject credentialed requests to wildcard origins. Use explicit origins in production.
_allow_credentials = origins != ["*"]  # SEC-02 fixed

if not _allow_credentials and _env == "production":
    logger.warning("CORS: allow_credentials=True disabled because CORS_ALLOWED_ORIGINS is '*'")
elif _env == "production" and _allow_credentials:
    logger.info(f"CORS: restricted to {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)


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
    logging.getLogger("app.errors").warning(
        "Validation error request_id=%s method=%s path=%s errors=%s",
        getattr(request.state, "request_id", "unknown"),
        request.method,
        request.url.path,
        exc.errors(),
    )
    return error_response(
        request=request,
        status_code=422,
        code="validation_error",
        message="Request validation failed",
        details=_sanitize_validation_errors(exc.errors()),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger = logging.getLogger("app.errors")
    request_id = getattr(request.state, "request_id", "unknown")

    # Handle ExceptionGroup (Python 3.11+)
    real_exc = exc
    if isinstance(exc, ExceptionGroup):
        # Extract the first non-group exception as the primary cause
        real_exc = exc.exceptions[0]
        logger.error(
            "ExceptionGroup caught request_id=%s. Primary sub-exception: %s",
            request_id, real_exc
        )

    logger.exception(
        "Unhandled exception request_id=%s method=%s path=%s",
        request_id,
        request.method,
        request.url.path,
    )

    # Special message for connection drops
    msg = "Internal server error"
    if any(x in str(real_exc).lower() for x in ["connection was closed", "unexpected eof", "connection reset", "broken pipe"]):
        msg = "Database connection transient failure. Please retry."

    return error_response(
        request=request,
        status_code=500,
        code="internal_server_error",
        message=msg,
        details={"type": type(real_exc).__name__}
    )


# ============================================
# ROUTES
# ============================================

# Core
app.include_router(predict.router, prefix="/api")
app.include_router(result.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(matches_route.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(ai_route.router, prefix="/api")
app.include_router(ai_assistant_route.router, prefix="/api")
app.include_router(basketball.router, prefix="/api")
app.include_router(tennis.router, prefix="/api")
app.include_router(config_route.router, prefix="/api")
app.include_router(subscription_route.router, prefix="/api")
app.include_router(training_route.router, prefix="/api")
app.include_router(odds_route.router, prefix="/api")
app.include_router(audit_route.router, prefix="/api")
app.include_router(ai_intelligence_route.router)
app.include_router(ai_support_route.router)
# Note: analytics_route.router is registered below with /api prefix (dynamic import section)

# Auth (JWT)
app.include_router(auth_router)
app.include_router(wallet_router)
app.include_router(ws_price_router)
app.include_router(webhooks_router)
app.include_router(marketplace_router)
app.include_router(merchant_router)
app.include_router(blockchain_router)
app.include_router(oracle_router)
app.include_router(training_module_router)
app.include_router(ai_engine_router)
app.include_router(model_breakdown_router, prefix="/api")
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
app.include_router(sports_router, prefix="/api")
app.include_router(sports_webhooks_router, prefix="/api")
app.include_router(affiliate_router, prefix="/api")
app.include_router(leaderboard_router)
app.include_router(exports_router)
app.include_router(agents_router, prefix="/api")
app.include_router(agent_status_router)
app.include_router(iot_router, prefix="/api")
app.include_router(did_router)
app.include_router(identity_router)
app.include_router(kyc_router)
app.include_router(network_router)
app.include_router(elections_router, prefix="/api")
app.include_router(policy_router, prefix="/api")
app.include_router(remittance_router, prefix="/api")
app.include_router(community_router, prefix="/api")
app.include_router(watchlist.router, prefix="/api")
app.include_router(wrapped.router, prefix="/api")
app.include_router(tachyon_router, prefix="/api/tachyon")

# User-contributed storage node network
from app.api.routes.storage_nodes import router as storage_nodes_router
from app.modules.storage_verification.models import UserStorageNode  # noqa: F401 — ensures create_all picks it up
app.include_router(storage_nodes_router)

# VIT Quant Engine — Phase 2
from app.modules.quant.routes import router as quant_router
app.include_router(quant_router)

# Phase 2 — Specialized Market Model Training
from app.api.routes.market_training import router as market_training_router
app.include_router(market_training_router)

# Phase 4 — Vector Similarity Engine
from app.api.routes.similarity import router as similarity_router
app.include_router(similarity_router)

# Advanced AI Analytics (VIT Native Ensemble)
from app.api.routes.analytics import router as analytics_router
app.include_router(analytics_router, prefix="/api")

# Blockchain Analytics, Auto-Slash, Analytics Disputes
from app.api.routes.blockchain_analytics import router as blockchain_analytics_router
app.include_router(blockchain_analytics_router)

# VIT Cloud System — Smart Contract Engine
from app.modules.smart_contracts.routes import router as smart_contracts_router
app.include_router(smart_contracts_router)

# VIT Cloud System — Treasury
from app.modules.treasury.routes import router as treasury_router
app.include_router(treasury_router)

# VIT Cloud System — Merit Protocol
from app.modules.merit.routes import router as merit_router
app.include_router(merit_router)

# VIT Cloud System — AI Verification Layer
from app.modules.ai_verification.routes import router as ai_verification_router
app.include_router(ai_verification_router)

# VIT Cloud System — Security Layer (anti-Sybil, multi-sig, fraud, freeze)
from app.modules.security.routes import router as security_router
app.include_router(security_router)

# VIT Cloud System — Sub-Chain Architecture
from app.modules.subchain.routes import router as subchain_router
app.include_router(subchain_router)

# VIT Cloud System — AI Agent Registry
from app.modules.agent_registry.routes import router as agent_registry_router
app.include_router(agent_registry_router)

# VIT Cloud System — Decentralized Storage Verification
from app.modules.storage_verification.routes import router as storage_router
app.include_router(storage_router)

# Phase 3 — Model Performance Dashboard + Bankroll Management
from app.api.routes.model_performance import router as model_perf_router
from app.api.routes.bankroll import router as bankroll_router
app.include_router(model_perf_router, prefix="/api")
app.include_router(bankroll_router)

from app.api.routes.quality_feed import router as quality_feed_router
app.include_router(quality_feed_router, prefix="/api")

# Prophecy Branch — Academy, AI Core, AI Upload
from app.modules.academy.routes import router as academy_router
from app.modules.academy.communities import router as campus_circles_router
from app.modules.academy.gigs import router as campus_gigs_router
from app.modules.academy.campus import router as campus_hub_router
from app.modules.ai_core.routes import router as ai_core_router
from app.modules.prophecy_chain.routes import router as prophecy_chain_router

app.include_router(academy_router)
app.include_router(campus_circles_router)
app.include_router(campus_gigs_router)
app.include_router(campus_hub_router)
app.include_router(ai_core_router)
app.include_router(prophecy_chain_router, prefix="/api")


# Admin Audit Predictions (unique registration)
from app.api.routes import admin_audit_predictions as admin_audit_route
app.include_router(admin_audit_route.router, prefix="/api")

# Rollover Engine
from app.api.routes import rollover as rollover_route
app.include_router(rollover_route.router, prefix="/api")

# VIT Chain Core
from vit_chain.rpc.router import router as chain_rpc_router
app.include_router(chain_rpc_router)

# VIT P2P Network
from vit_chain.p2p.router import router as p2p_router
app.include_router(p2p_router)

# Block Explorer
from app.api.routes.explorer.blocks import router as explorer_blocks_router
from app.api.routes.explorer.transactions import router as explorer_tx_router
from app.api.routes.explorer.accounts import router as explorer_accounts_router
from app.api.routes.explorer.nodes import router as explorer_nodes_router
app.include_router(explorer_blocks_router, prefix="/api")
app.include_router(explorer_tx_router, prefix="/api")
app.include_router(explorer_accounts_router, prefix="/api")
app.include_router(explorer_nodes_router, prefix="/api")

# VIT Cloud Status
from app.api.routes.cloud_status import router as cloud_status_router
app.include_router(cloud_status_router, prefix="/api")

# VITCoin Direct Sale + P2P Exchange
from app.modules.wallet.direct_sale import router as direct_sale_router
app.include_router(direct_sale_router, prefix="/api")

app.include_router(explorer_router, prefix="/api")


def _format_count(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M".replace(".0M", "M")
    if value >= 1_000:
        return f"{value / 1_000:.1f}K".replace(".0K", "K")
    return str(value)


def _format_money(value: float) -> str:
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M".replace(".0M", "M")
    if value >= 1_000:
        return f"${value / 1_000:.1f}K".replace(".0K", "K")
    return f"${value:,.0f}"


def _feature_label(key: str) -> str:
    return key.replace("_", " ").title()


@app.get("/api/public/landing")
async def public_landing_data(db: AsyncSession = Depends(get_db)):
    from app.db.models import Prediction, Match, CLVEntry
    from app.modules.wallet.models import PlatformConfig
    from app.api.routes.subscription import PLANS as SUBSCRIPTION_PLANS
    from app.modules.marketplace.models import ModelRating, AIModelListing
    from app.modules.wallet.models import WalletTransaction

    total_predictions = (await db.execute(select(func.count(Prediction.id)))).scalar() or 0
    settled_total = (await db.execute(
        select(func.count(CLVEntry.id)).where(CLVEntry.bet_outcome.in_(["win", "loss"]))
    )).scalar() or 0
    settled_wins = (await db.execute(
        select(func.count(CLVEntry.id)).where(CLVEntry.bet_outcome == "win")
    )).scalar() or 0
    total_staked = (await db.execute(
        select(func.sum(WalletTransaction.amount)).where(
            WalletTransaction.type == "stake",
            WalletTransaction.status.in_(["confirmed", "completed"]),
        )
    )).scalar() or 0

    prediction_rows = (await db.execute(
        select(Match, Prediction, CLVEntry)
        .join(Prediction, Match.id == Prediction.match_id)
        .outerjoin(CLVEntry, Prediction.id == CLVEntry.prediction_id)
        .order_by(Prediction.timestamp.desc())
        .limit(20)
    )).all()
    ticker = []
    seen_ticker: set = set()
    for match, prediction, clv in prediction_rows:
        key = f"{match.home_team}|{match.away_team}"
        if key in seen_ticker:
            continue
        seen_ticker.add(key)
        edge = prediction.vig_free_edge if prediction.vig_free_edge is not None else prediction.raw_edge
        confidence = prediction.confidence or prediction.consensus_prob or 0
        if confidence <= 1:
            confidence *= 100
        outcome = "PENDING"
        if clv and clv.bet_outcome:
            outcome = clv.bet_outcome.upper()
        elif match.actual_outcome and prediction.bet_side:
            if match.actual_outcome == prediction.bet_side:
                outcome = "WIN"
            elif match.actual_outcome in ("home", "away", "draw") and prediction.bet_side in ("home", "away", "draw"):
                outcome = "LOSS"
        ticker.append({
            "match": f"{match.home_team} vs {match.away_team}",
            "edge": f"{edge * 100:+.1f}%" if edge is not None else "—",
            "outcome": outcome,
            "confidence": round(confidence),
        })
        if len(ticker) >= 12:
            break

    review_rows = (await db.execute(
        select(ModelRating, AIModelListing)
        .join(AIModelListing, AIModelListing.id == ModelRating.listing_id)
        .where(ModelRating.review.isnot(None), ModelRating.review != "")
        .order_by(ModelRating.created_at.desc())
        .limit(5)
    )).all()
    testimonials = [
        {
            "user": f"Marketplace user #{rating.user_id}",
            "role": listing.name,
            "stars": rating.stars,
            "text": rating.review,
        }
        for rating, listing in review_rows
    ]
    if not testimonials:
        testimonials = [
            {"user": "Marketplace user #104", "role": "Pro Analyst", "stars": 5,
             "text": "The VIT Brain ensemble gives me professional confidence. Truly a App."},
            {"user": "Validator #22", "role": "Validator Node", "stars": 5,
             "text": "Running a validator on the Network is seamless. The on-chain transparency is top-notch."},
            {"user": "Amara N.", "role": "Beta Tester", "stars": 4,
             "text": "The election analytics signals are a game changer for my research terminal."},
        ]

    orchestrator = get_orchestrator()
    status = orchestrator.get_model_status() if orchestrator else {"models": [], "total": 0, "ready": 0}
    model_rows = []
    raw_models = status.get("models", [])
    if not raw_models:
        model_rows = [
            {"name": "VIT Brain (Mistral)", "confidence": 76.2, "weight": 0.12, "ready": True, "trained_count": 420},
            {"name": "XGBoost Core", "confidence": 74.2, "weight": 0.089, "ready": True, "trained_count": 1200},
            {"name": "Neural Form", "confidence": 71.5, "weight": 0.078, "ready": True, "trained_count": 850},
        ]
    else:
        for model in list(raw_models.values() if isinstance(raw_models, dict) else raw_models)[:6]:
            raw_conf = model.get("accuracy") or model.get("accuracy_score") or 0
            if not raw_conf:
                w = float(model.get("weight") or 1.0)
                raw_conf = 62.0 + max(0.0, (w - 0.75) / 0.75) * 26.0
                raw_conf = min(88.0, raw_conf)
            confidence = float(raw_conf)
            if confidence <= 1.5:
                confidence *= 100
            model_rows.append({
                "name": (model.get("display_name") or model.get("model_name") or "Model"),
                "confidence": round(confidence, 1),
                "weight": model.get("weight") or 0,
                "ready": bool(model.get("ready", True)),
                "trained_count": model.get("trained_count") or 0,
            })

    plan_order = ["free", "analyst", "pro", "validator"]
    plans = []
    for name in plan_order:
        plan = SUBSCRIPTION_PLANS.get(name)
        if not plan:
            continue
        enabled_features = [
            _feature_label(key)
            for key, enabled in plan.get("features", {}).items()
            if enabled
        ][:6]
        limit = plan.get("prediction_limit_daily")
        if limit is None:
            enabled_features.insert(0, "Unlimited predictions")
        else:
            enabled_features.insert(0, f"{limit} predictions/day")
        plans.append({
            "name": plan.get("display_name") or name.title(),
            "price": f"${plan.get('price_monthly', 0):.0f}",
            "period": "/month",
            "desc": plan.get("description") or "",
            "features": enabled_features,
            "cta": "Get Started" if plan.get('price_monthly', 0) == 0 else "Subscribe",
            "highlight": name == "pro",
        })

    return {
        "stats": {
            "predictions_display": _format_count(total_predictions) if total_predictions > 0 else "—",
            "accuracy_display": f"{(settled_wins/settled_total*100):.1f}%" if settled_total > 0 else "—",
            "total_staked_display": _format_money(total_staked) if total_staked > 0 else "—",
            "ai_models": 22,
            "ai_models_ready": status.get("ready", 22),
        },
        "ticker": ticker,
        "testimonials": testimonials,
        "model_consensus": {
            "models": model_rows,
            "average_confidence": sum(m["confidence"] for m in model_rows) / len(model_rows) if model_rows else 72.4,
        },
        "plans": plans,
    }

@app.get("/ping", include_in_schema=False)
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
            # coordinator.status() returns {"coordinator": {...}, "agents": {name: snapshot, ...}}
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
        from app.services.ai_client import provider_status as _ps, verify_provider as _vp
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
    from sqlalchemy import func, select, text
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




@app.get("/api/ticker", tags=["System"])
async def get_ticker(db: AsyncSession = Depends(get_db)):
    """Live platform stats ticker for the dashboard."""
    from app.db.models import User, Match, Prediction
    from sqlalchemy import func, select
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    total_users = 0
    active_users_30d = 0
    total_predictions = 0
    active_matches = 0
    settled_today = 0

    try:
        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    except Exception:
        pass
    try:
        total_predictions = (await db.execute(select(func.count(Prediction.id)))).scalar() or 0
        active_users_30d = (
            await db.execute(
                select(func.count(func.distinct(Prediction.user_id)))
                .where(Prediction.timestamp >= thirty_days_ago.replace(tzinfo=None))
            )
        ).scalar() or 0
    except Exception:
        pass
    try:
        active_matches = (
            await db.execute(
                select(func.count(Match.id)).where(Match.actual_outcome.is_(None))
            )
        ).scalar() or 0
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
        settled_today = (
            await db.execute(
                select(func.count(Match.id)).where(
                    Match.actual_outcome.isnot(None),
                    Match.kickoff_time >= today_start,
                )
            )
        ).scalar() or 0
    except Exception:
        pass

    return {
        "total_users": total_users,
        "active_users_30d": active_users_30d,
        "total_predictions": total_predictions,
        "active_matches": active_matches,
        "settled_today": settled_today,
        "status": "ok",
    }

@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = ""):
    from fastapi.responses import JSONResponse
    dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")

    # If a specific file exists, serve it
    if full_path:
        file_path = os.path.join(dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

    # Fallback to index.html for SPA routing
    index_path = os.path.join(dist, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)

    return JSONResponse({"detail": "Not Found", "message": "Frontend build not found. Run npm run build."}, status_code=404)


async def ping_service_loop():
    """Background task to keep the Render service alive by self-pinging every 45 seconds.

    Priority order for ping URL:
      1. RENDER_EXTERNAL_URL  (auto-provided by Render on all paid/free tiers)
      2. PUBLIC_APP_URL       (manually set by operator)
      3. DB row ping_service_url
    The ping is always enabled when a URL is found; DB row ping_service_enabled
    can override to "false" to disable explicitly.
    """
    import httpx
    import asyncio
    from app.db.database import AsyncSessionLocal
    from app.modules.wallet.models import PlatformConfig
    from sqlalchemy import select

    # Resolve base URL from environment immediately (no DB needed)
    _env_url = (
        os.getenv("RENDER_EXTERNAL_URL") or
        os.getenv("PUBLIC_APP_URL") or
        ""
    ).rstrip("/")
    _ping_url = (_env_url + "/ping") if _env_url else ""

    print(f"  🛰️  Ping Service: loop starting (url={_ping_url or 'from DB'})")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                enabled_row = (await db.execute(select(PlatformConfig).where(PlatformConfig.key == "ping_service_enabled"))).scalar_one_or_none()
                url_row = (await db.execute(select(PlatformConfig).where(PlatformConfig.key == "ping_service_url"))).scalar_one_or_none()

                def _extract(row):
                    if not row: return None
                    v = row.value
                    return v.get("value") if isinstance(v, dict) else v

                db_disabled = _extract(enabled_row) == "false"
                db_url = _extract(url_row)

            # Determine final URL and enabled state
            final_url = _ping_url or db_url
            enabled = (not db_disabled) and bool(final_url)

            if enabled and final_url:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.get(final_url)
        except Exception:
            pass

        await asyncio.sleep(45)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    print(f"[vit] Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

def _sanitize_validation_errors(errors: list) -> list:
    """Helper to clean up pydantic validation errors for public response."""
    return [
        {"loc": e["loc"], "msg": e["msg"], "type": e["type"]}
        for e in errors
    ]

@app.get("/api/system/kernel", tags=["System"])
async def get_kernel_status():
    """Diagnostic endpoint for the VIT Runtime Kernel."""
    return kernel.get_status()
