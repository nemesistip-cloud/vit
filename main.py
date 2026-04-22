# main.py — VIT Sports Intelligence Network v4.6.0
# Full Integration: AI + Wallet + Blockchain + Training

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
from app.config import get_env, APP_VERSION, print_config_status
from app.core.errors import AppError, error_response
from app.db.database import get_db
import app.db.models  # ensure all models registered
import app.modules.wallet.models  # register wallet models with SQLAlchemy
import app.modules.blockchain.models  # register blockchain models with SQLAlchemy
import app.modules.training.models  # register training module models with SQLAlchemy
import app.modules.ai.models  # register Module E models (ModelMetadata, AIPredictionAudit)
import app.data.models  # register Module F models (MatchFeatureStore, PipelineRun)
import app.modules.notifications.models  # register Module K notification models
import app.modules.marketplace.models    # register Module G marketplace models
import app.modules.trust.models          # register Module I trust models
import app.modules.bridge.models         # register Module J bridge models
import app.modules.developer.models      # register Module L developer models
import app.modules.governance.models     # register Module M governance models
import app.modules.referral.models       # register referral models

# ===== CORE ROUTES =====
from app.api.routes import (
    predict,
    result,
    history,
    admin,
    ai_feed,
    ai as ai_route,
    config as config_route,
    training as training_route,
    analytics as analytics_route,
    odds_compare as odds_route,
    subscription as subscription_route,
    audit as audit_route,
    matches as matches_route,
)

# ===== AUTH ROUTES =====
from app.auth.routes import router as auth_router

# ===== WALLET ROUTES (Phase 1) =====
from app.modules.wallet.routes import router as wallet_router
from app.modules.wallet.admin_routes import router as wallet_admin_router
from app.modules.wallet.webhooks import router as webhooks_router

# ===== BLOCKCHAIN ROUTES (Phase 4) =====
from app.modules.blockchain.routes import router as blockchain_router
from app.modules.blockchain.oracle import router as oracle_router

# ===== TRAINING MODULE ROUTES (Module D) =====
from app.modules.training.routes import router as training_module_router

# ===== AI ORCHESTRATION ROUTES (Module E) =====
from app.modules.ai.routes import router as ai_engine_router

# ===== DASHBOARD ROUTES =====
from app.api.routes.dashboard import router as dashboard_router

# ===== DATA PIPELINE ROUTES (Module F) =====
from app.data.routes import router as pipeline_router
from app.data.pipeline import etl_pipeline_loop, odds_refresh_loop
from app.core.cache import cache_background_purge_loop

# ===== NOTIFICATION ROUTES (Module K) =====
from app.modules.notifications.routes import router as notifications_router
from app.modules.notifications.websocket import router as notifications_ws_router

# ===== MARKETPLACE ROUTES (Module G) =====
from app.modules.marketplace.routes import router as marketplace_router

# ===== TRUST ROUTES (Module I) =====
from app.modules.trust.routes import router as trust_router

# ===== BRIDGE ROUTES (Module J) =====
from app.modules.bridge.routes import router as bridge_router

# ===== DEVELOPER ROUTES (Module L) =====
from app.modules.developer.routes import router as developer_router

# ===== GOVERNANCE ROUTES (Module M) =====
from app.modules.governance.routes import router as governance_router

# ===== NEW FEATURE ROUTES =====
from app.auth.verification import router as verification_router
from app.auth.totp import router as totp_router
from app.modules.referral.routes import router as referral_router
from app.api.routes.leaderboard import router as leaderboard_router
from app.api.routes.exports import router as exports_router

# ===== MIDDLEWARE =====
from app.api.middleware.auth import APIKeyMiddleware
from app.api.middleware.logging import LoggingMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.middleware.security import SecurityHeadersMiddleware

# ===== SERVICES =====
from app.schemas.schemas import HealthResponse
from app.services.alerts import TelegramAlert
from app.core.dependencies import (
    get_orchestrator,
    get_data_loader,
    get_telegram_alerts,
)

# ===== BACKGROUND TASKS =====
from app.services.model_accountability import ModelAccountability
from app.services.results_settler import settle_results
# from app.wallet.pricing import recalculate_vitcoin_price

load_dotenv()

logger = logging.getLogger("uvicorn.error")

# ============================================
# BACKGROUND TASKS
# ============================================

_SETTLEMENT_INTERVAL_HOURS = 0.5  # run every 30 minutes
_ACCOUNTABILITY_INTERVAL_HOURS = 24
_VITCOIN_PRICING_INTERVAL_HOURS = 6


class BackgroundTaskSupervisor:
    def __init__(self, task_specs, check_interval: int = 30, max_restarts: int = 5):
        self.task_specs = task_specs
        self.check_interval = check_interval
        self.max_restarts = max_restarts
        self.tasks = {}
        self.restart_counts = {name: 0 for name, _ in task_specs}
        self.last_started_at = {}
        self.monitor_task = None
        self.stopping = False

    def start(self):
        for name, factory in self.task_specs:
            self._start_task(name, factory)
        self.monitor_task = asyncio.create_task(self._monitor(), name="background-supervisor")
        logger.info("[supervisor] started with tasks=%s", ", ".join(self.tasks.keys()))

    def _start_task(self, name, factory):
        task = asyncio.create_task(factory(), name=name)
        self.tasks[name] = task
        self.last_started_at[name] = time.time()
        logger.info("[supervisor] task started name=%s", name)

    async def _monitor(self):
        while not self.stopping:
            await asyncio.sleep(self.check_interval)
            for name, factory in self.task_specs:
                task = self.tasks.get(name)
                if task and not task.done():
                    continue
                if self.restart_counts[name] >= self.max_restarts:
                    logger.critical("[supervisor] task restart limit reached name=%s restarts=%s", name, self.restart_counts[name])
                    try:
                        _alerts = get_telegram_alerts()
                        if _alerts and _alerts.enabled:
                            await _alerts.send_message(
                                f"🚨 <b>Background Task DEAD</b>\n"
                                f"Task <code>{name}</code> has exceeded max restarts ({self.max_restarts}).\n"
                                f"Manual intervention required."
                            )
                    except Exception:
                        pass
                    continue
                if task:
                    try:
                        exc = task.exception()
                    except asyncio.CancelledError:
                        exc = None
                    if exc:
                        logger.error("[supervisor] task failed name=%s error=%s", name, exc, exc_info=exc)
                    else:
                        logger.warning("[supervisor] task exited name=%s", name)
                self.restart_counts[name] += 1
                logger.warning("[supervisor] restarting task name=%s attempt=%s", name, self.restart_counts[name])
                self._start_task(name, factory)

    async def stop(self):
        self.stopping = True
        all_tasks = list(self.tasks.values())
        if self.monitor_task:
            all_tasks.append(self.monitor_task)
        for task in all_tasks:
            task.cancel()
        await asyncio.gather(*all_tasks, return_exceptions=True)
        logger.info("[supervisor] stopped")

    def snapshot(self):
        return {
            name: {
                "running": bool(task and not task.done()),
                "done": bool(task and task.done()),
                "restarts": self.restart_counts.get(name, 0),
                "last_started_at": self.last_started_at.get(name),
            }
            for name, task in self.tasks.items()
        }


async def auto_settle_loop():
    await asyncio.sleep(60)
    while True:
        if os.getenv("FOOTBALL_DATA_API_KEY"):
            try:
                from app.db.database import AsyncSessionLocal
                from app.modules.ai.weight_adjuster import adjust_weights_for_match
                # Use days_back=7 to catch any backlog of unsettled matches
                settlement_result = await settle_results(days_back=7)
                if settlement_result.get("settled", 0) > 0 or settlement_result.get("errors", 0) > 0:
                    print(f"[settlement] {settlement_result.get('message')} | errors={settlement_result.get('errors',0)}")

                # E3 — weight adjustment for each newly settled match
                if isinstance(settlement_result, dict):
                    settled_matches = settlement_result.get("details", settlement_result.get("matches", []))
                elif isinstance(settlement_result, list):
                    settled_matches = settlement_result
                else:
                    settled_matches = []
                if settled_matches:
                    orch = get_orchestrator()
                    async with AsyncSessionLocal() as db:
                        for match_info in settled_matches:
                            mid = str(match_info.get("match_id", ""))
                            outcome = match_info.get("outcome")
                            if mid and outcome:
                                await adjust_weights_for_match(db, orch, mid, outcome)
            except Exception as e:
                print(f"[settlement] ERROR: {e}")
        await asyncio.sleep(_SETTLEMENT_INTERVAL_HOURS * 3600)


async def model_accountability_loop():
    from app.db.database import AsyncSessionLocal

    await asyncio.sleep(120)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                ma = ModelAccountability(db)
                await ma.update_model_weights()
                print("[accountability] updated")
        except Exception as e:
            print(f"[accountability] ERROR: {e}")

        await asyncio.sleep(_ACCOUNTABILITY_INTERVAL_HOURS * 3600)


async def live_match_tracker_loop():
    """
    Polls Football-Data API every 2 minutes.
    - Marks IN_PLAY matches as 'live' with current scores
    - Marks FINISHED matches as 'completed' immediately with final scores
    - Triggers a full settlement pass every cycle
    """
    import httpx as _httpx
    from difflib import SequenceMatcher as _SM
    from datetime import datetime as _dt, timedelta as _td

    _LIVE_POLL_INTERVAL = 120  # seconds

    COMP_MAP = {
        "PL": "premier_league", "PD": "la_liga", "BL1": "bundesliga",
        "SA": "serie_a", "FL1": "ligue_1", "DED": "eredivisie",
        "ELC": "championship", "PPL": "primeira_liga",
    }

    def _sim(a: str, b: str) -> float:
        return _SM(None, a.lower(), b.lower()).ratio()

    def _names_match(a: str, b: str) -> bool:
        if a.lower() == b.lower():
            return True
        for suf in [" FC", " AFC", " CF", " SC"]:
            a = a.replace(suf, "")
            b = b.replace(suf, "")
        return _sim(a.strip(), b.strip()) >= 0.72

    await asyncio.sleep(90)
    while True:
        try:
            football_key = os.getenv("FOOTBALL_DATA_API_KEY", "")
            if football_key:
                from app.db.database import AsyncSessionLocal
                from app.db.models import Match
                from sqlalchemy import select as _sel

                # Load all unsettled matches once
                async with AsyncSessionLocal() as db:
                    unsettled_q = await db.execute(_sel(Match).where(Match.actual_outcome.is_(None)))
                    unsettled_matches = unsettled_q.scalars().all()

                now_utc = _dt.utcnow()

                async with _httpx.AsyncClient(timeout=15) as client:
                    for code, league in COMP_MAP.items():
                        # Poll both IN_PLAY and FINISHED in one call using TIMED status
                        date_from = (now_utc - _td(hours=6)).strftime("%Y-%m-%d")
                        date_to   = now_utc.strftime("%Y-%m-%d")
                        for api_status in ("IN_PLAY", "FINISHED"):
                            try:
                                params = {"status": api_status}
                                if api_status == "FINISHED":
                                    params["dateFrom"] = date_from
                                    params["dateTo"]   = date_to
                                r = await client.get(
                                    f"https://api.football-data.org/v4/competitions/{code}/matches",
                                    headers={"X-Auth-Token": football_key},
                                    params=params,
                                )
                                if r.status_code in (401, 403):
                                    break  # skip this competition on auth error, do not blacklist
                                if r.status_code != 200:
                                    continue

                                api_matches = r.json().get("matches", [])
                                if not api_matches:
                                    continue

                                async with AsyncSessionLocal() as db:
                                    for api_m in api_matches:
                                        home_name = api_m["homeTeam"]["name"]
                                        away_name = api_m["awayTeam"]["name"]
                                        _score_obj = api_m.get("score", {})

                                        # For live: use currentScore → halfTime → fullTime
                                        # For finished: use fullTime
                                        if api_status == "IN_PLAY":
                                            score = (_score_obj.get("currentScore") or
                                                     _score_obj.get("halfTime") or
                                                     _score_obj.get("fullTime") or {})
                                        else:
                                            score = _score_obj.get("fullTime") or {}

                                        home_g = score.get("home")
                                        away_g = score.get("away")

                                        # Find matching DB record with kickoff proximity check
                                        api_kickoff_str = api_m.get("utcDate", "")
                                        api_kickoff = None
                                        if api_kickoff_str:
                                            try:
                                                api_kickoff = _dt.fromisoformat(api_kickoff_str.replace("Z", "+00:00")).replace(tzinfo=None)
                                            except Exception:
                                                pass

                                        db_match = None
                                        for m in unsettled_matches:
                                            if not _names_match(home_name, m.home_team):
                                                continue
                                            if not _names_match(away_name, m.away_team):
                                                continue
                                            # Kickoff proximity: within 36 hours
                                            if api_kickoff and m.kickoff_time:
                                                delta = abs((m.kickoff_time - api_kickoff).total_seconds())
                                                if delta > 36 * 3600:
                                                    continue
                                            db_match = m
                                            break

                                        if not db_match:
                                            continue

                                        changed = False
                                        if api_status == "IN_PLAY" and db_match.status != "live":
                                            db_match.status = "live"
                                            changed = True
                                        elif api_status == "FINISHED" and home_g is not None and away_g is not None:
                                            if db_match.home_goals != home_g or db_match.away_goals != away_g or db_match.actual_outcome is None:
                                                db_match.home_goals = home_g
                                                db_match.away_goals = away_g
                                                db_match.actual_outcome = (
                                                    "home" if home_g > away_g else
                                                    "draw" if home_g == away_g else "away"
                                                )
                                                db_match.status = "completed"
                                                changed = True
                                                print(f"[live-tracker] Completed: {home_name} {home_g}-{away_g} {away_name}")

                                        if changed:
                                            await db.commit()
                                            # Refresh unsettled list after commit
                                            if api_status == "FINISHED" and db_match in unsettled_matches:
                                                unsettled_matches.remove(db_match)

                            except Exception as e:
                                print(f"[live-tracker] {league}/{api_status}: {e}")
                                continue

                # After checking live/finished, settle any DB-completed matches
                # (no extra API calls — the full API pass happens every 30 min)
                from app.services.results_settler import settle_completed_db_matches as _settle_db
                sr = await _settle_db()
                if sr.get("settled", 0) > 0:
                    print(f"[live-tracker] DB settlement: settled={sr['settled']} errors={sr.get('errors',0)}")

        except Exception as e:
            print(f"[live-tracker] ERROR: {e}")

        await asyncio.sleep(_LIVE_POLL_INTERVAL)


async def vitcoin_pricing_loop():
    """Recalculate VITCoin price every 6 hours based on revenue and supply."""
    await asyncio.sleep(30)
    while True:
        try:
            from app.db.database import AsyncSessionLocal
            from app.modules.wallet.pricing import VITCoinPricingEngine
            from app.modules.wallet.models import PlatformConfig, VITCoinPriceHistory
            from sqlalchemy import select as _sel
            from decimal import Decimal

            async with AsyncSessionLocal() as db:
                engine = VITCoinPricingEngine(db)
                supply = await engine.get_circulating_supply()
                revenue_30d = await engine.get_rolling_revenue(days=30)

                # Revenue-backed price: price = (revenue * multiplier) / supply
                # With a floor of $0.001
                if supply > 0 and revenue_30d > 0:
                    raw_price = (revenue_30d * Decimal("12")) / supply
                else:
                    raw_price = Decimal("0")

                # Floor price from config
                floor_res = await db.execute(
                    _sel(PlatformConfig).where(PlatformConfig.key == "vitcoin_price_floor")
                )
                floor_cfg = floor_res.scalar_one_or_none()
                floor = Decimal(str((floor_cfg.value or {}).get("amount", "0.001"))) if floor_cfg else Decimal("0.001")

                new_price = max(raw_price, floor)

                db.add(VITCoinPriceHistory(
                    price_usd=new_price,
                    circulating_supply=supply,
                    rolling_revenue_usd=revenue_30d,
                ))
                await db.commit()
                print(f"[pricing] VITCoin price updated: ${new_price:.6f} USD (supply={supply}, 30d_revenue={revenue_30d})")
        except Exception as e:
            print(f"[pricing] ERROR: {e}")
        await asyncio.sleep(_VITCOIN_PRICING_INTERVAL_HOURS * 3600)


async def subscription_expiry_loop():
    """Module K — check every 12h and warn users about expiring subscriptions."""
    from app.db.database import AsyncSessionLocal
    from app.modules.notifications.service import NotificationService
    while True:
        await asyncio.sleep(12 * 3600)
        try:
            async with AsyncSessionLocal() as db:
                await NotificationService.check_subscription_expiry(db)
        except Exception as e:
            print(f"[notifications] subscription expiry check error: {e}")


# ============================================
# LIFECYCLE
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.logging_config import configure_logging
    configure_logging(level=get_env("LOG_LEVEL", "INFO"))
    print_config_status()
    print(f"🚀 VIT Network v{APP_VERSION} starting...")

    try:
        from app.db.database import engine
        from app.modules.referral.models import ReferralCode, ReferralUse
        async with engine.begin() as conn:
            await conn.run_sync(ReferralCode.__table__.create, checkfirst=True)
            await conn.run_sync(ReferralUse.__table__.create, checkfirst=True)
            dialect = conn.dialect.name
            if dialect == "sqlite":
                cols = (await conn.execute(text("PRAGMA table_info(predictions)"))).fetchall()
                col_names = {row[1] for row in cols}
                if "user_id" not in col_names:
                    await conn.execute(text("ALTER TABLE predictions ADD COLUMN user_id INTEGER"))
                user_cols = (await conn.execute(text("PRAGMA table_info(users)"))).fetchall()
                user_col_names = {row[1] for row in user_cols}
                user_additions = {
                    "kyc_status": "VARCHAR(20) DEFAULT 'none'",
                    "kyc_submitted_at": "DATETIME",
                    "kyc_data": "JSON",
                    "current_streak": "INTEGER DEFAULT 0",
                    "best_streak": "INTEGER DEFAULT 0",
                    "total_xp": "INTEGER DEFAULT 0",
                }
                for col, ddl in user_additions.items():
                    if col not in user_col_names:
                        await conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {ddl}"))

                # ── marketplace_listings new columns ────────────────────────
                try:
                    mkt_cols = (await conn.execute(text("PRAGMA table_info(marketplace_listings)"))).fetchall()
                    mkt_col_names = {row[1] for row in mkt_cols}
                    mkt_additions = {
                        "listing_fee_paid": "NUMERIC(20,8) DEFAULT 0",
                        "pkl_path":         "VARCHAR(512)",
                        "file_size_bytes":  "INTEGER",
                        "pkl_sha256":       "VARCHAR(64)",
                        "webhook_url":      "VARCHAR(512)",
                        "webhook_secret":   "VARCHAR(256)",
                        "approval_status":  "VARCHAR(20) DEFAULT 'pending'",
                        "approval_note":    "TEXT",
                        "approved_by":      "INTEGER",
                        "approved_at":      "DATETIME",
                        "error_message":    "TEXT",
                    }
                    for col, ddl in mkt_additions.items():
                        if col not in mkt_col_names:
                            await conn.execute(text(f"ALTER TABLE marketplace_listings ADD COLUMN {col} {ddl}"))
                    # Also check marketplace_usage_logs
                    usage_cols = (await conn.execute(text("PRAGMA table_info(marketplace_usage_logs)"))).fetchall()
                    usage_col_names = {row[1] for row in usage_cols}
                    if "error_message" not in usage_col_names:
                        await conn.execute(text("ALTER TABLE marketplace_usage_logs ADD COLUMN error_message TEXT"))
                except Exception as _mkt_e:
                    print(f"⚠️  marketplace column migration skipped: {_mkt_e}")
            else:
                await conn.execute(text("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS user_id INTEGER"))
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_status VARCHAR(20) DEFAULT 'none'"))
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_submitted_at TIMESTAMP WITH TIME ZONE"))
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_data JSON"))
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS current_streak INTEGER DEFAULT 0"))
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS best_streak INTEGER DEFAULT 0"))
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS total_xp INTEGER DEFAULT 0"))
                # ── marketplace_listings new columns (PostgreSQL) ───────────
                try:
                    for col, ddl in [
                        ("listing_fee_paid", "NUMERIC(20,8) DEFAULT 0"),
                        ("pkl_path",         "VARCHAR(512)"),
                        ("file_size_bytes",  "INTEGER"),
                        ("pkl_sha256",       "VARCHAR(64)"),
                        ("webhook_url",      "VARCHAR(512)"),
                        ("webhook_secret",   "VARCHAR(256)"),
                        ("approval_status",  "VARCHAR(20) DEFAULT 'pending'"),
                        ("approval_note",    "TEXT"),
                        ("approved_by",      "INTEGER"),
                        ("approved_at",      "TIMESTAMP WITH TIME ZONE"),
                    ]:
                        await conn.execute(text(f"ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS {col} {ddl}"))
                    await conn.execute(text("ALTER TABLE marketplace_usage_logs ADD COLUMN IF NOT EXISTS error_message TEXT"))
                except Exception as _mkt_e:
                    print(f"⚠️  marketplace column migration skipped: {_mkt_e}")
    except Exception as _e:
        print(f"⚠️  Compatibility schema update skipped: {_e}")

    print("✅ Database migrations applied")

    # BACKFILL MATCH FINGERPRINTS (idempotent, only fills NULLs)
    try:
        from app.db.database import AsyncSessionLocal
        from app.data.match_dedup import backfill_fingerprints
        async with AsyncSessionLocal() as _db:
            updated = await backfill_fingerprints(_db)
        if updated:
            print(f"✅ Backfilled fingerprints on {updated} matches")
    except Exception as _e:
        print(f"⚠️  Match fingerprint backfill skipped: {_e}")

    # SEED PLATFORM CONFIG DEFAULTS
    try:
        from app.db.database import AsyncSessionLocal
        from app.modules.wallet.models import PlatformConfig
        from sqlalchemy import select as _select

        _default_configs = [
            ("fee_rates", {"deposit": 0.01, "withdrawal": 0.02, "conversion": 0.005}, "Platform fee rates"),
            ("vitcoin_min_stake", {"amount": 10, "validator_min": 100}, "Minimum VITCoin stake amounts"),
            ("withdrawal_limits", {"daily_usd": 1000, "daily_ngn": 500000, "daily_usdt": 1000}, "Daily withdrawal limits"),
            ("deposit_limits", {"min_usd": 1, "min_ngn": 500, "max_usd": 10000}, "Deposit limits"),
            ("vitcoin_supply", {"initial": 1000000, "burned": 0, "reserved": 100000}, "VITCoin supply parameters"),
            ("platform_treasury", {"address": "vit_treasury_001"}, "Platform treasury wallet reference"),
            ("exchange_rates", {"usd_ngn": 1580, "usd_pi": 0.5, "usd_usdt": 1.0}, "Fiat/crypto exchange rates"),
            ("vitcoin_price_formula", {"window_days": 30, "method": "revenue_backed"}, "VITCoin price calculation parameters"),
            ("vitcoin_price_floor", {"amount": "0.10"}, "Minimum VITCoin price in USD"),
            ("exchange_rates_usd",
             {"NGN": 0.000633, "USD": 1.0, "USDT": 1.0, "PI": 0.314159, "VITCoin": 0.10},
             "Per-currency rate to 1 USD (used by the conversion engine)"),
            ("conversion_fee_pct", {"value": 0.5}, "Currency conversion fee percentage"),
        ]
        async with AsyncSessionLocal() as _db:
            for key, value, desc in _default_configs:
                existing = (await _db.execute(_select(PlatformConfig).where(PlatformConfig.key == key))).scalar_one_or_none()
                if not existing:
                    _db.add(PlatformConfig(key=key, value=value, description=desc))
                elif key == "vitcoin_price_floor":
                    # One-shot heal: drop legacy $1.00 floor that disagreed with
                    # the conversion engine's $0.10 default.
                    try:
                        from decimal import Decimal as _D
                        cur = _D(str((existing.value or {}).get("amount", "0.10")))
                        if cur >= _D("1.00"):
                            existing.value = value
                    except Exception:
                        pass
            await _db.commit()
        print("✅ PlatformConfig defaults seeded")
    except Exception as _e:
        print(f"⚠️  PlatformConfig seeding failed: {_e}")

    # SEED DEFAULT ADMIN ACCOUNT
    try:
        import os as _os
        from app.db.database import AsyncSessionLocal
        from app.db.models import User as _User
        from app.auth.jwt_utils import hash_password
        from sqlalchemy import select as _select

        _admin_email = _os.environ.get("ADMIN_EMAIL", "admin@vit.network")
        _admin_pass = _os.environ.get("ADMIN_PASSWORD")
        _admin_user = _os.environ.get("ADMIN_USERNAME", "vit_admin")

        async with AsyncSessionLocal() as _db:
            _exists = (await _db.execute(_select(_User).where(_User.email == _admin_email))).scalar_one_or_none()
            if not _exists:
                if not _admin_pass:
                    print("⚠️  Default admin creation skipped: set ADMIN_PASSWORD or register the first user")
                else:
                    _db.add(_User(
                        email=_admin_email,
                        username=_admin_user,
                        hashed_password=hash_password(_admin_pass),
                        role="admin",
                        admin_role="super_admin",
                        subscription_tier="elite",
                        is_active=True,
                    ))
                    await _db.commit()
                    print(f"✅ Default admin created: {_admin_email}")
            else:
                # Ensure existing admin has admin_role and subscription_tier set
                if not _exists.admin_role:
                    _exists.admin_role = "super_admin"
                if not _exists.subscription_tier:
                    _exists.subscription_tier = "elite"
                await _db.commit()
                print(f"✅ Admin account found: {_admin_email}")
    except Exception as _e:
        print(f"⚠️  Admin seeding failed: {_e}")

    # SEED SUBSCRIPTION PLANS
    try:
        from app.db.database import AsyncSessionLocal
        from app.db.models import SubscriptionPlan
        from sqlalchemy import select as _select

        _plans = [
            {
                "name": "free",
                "display_name": "Free",
                "price_monthly": 0.0,
                "price_yearly": 0.0,
                "prediction_limit": 5,
                "features": {
                    "predictions": True,
                    "basic_history": True,
                    "advanced_analytics": False,
                    "ai_insights": False,
                    "accumulator_builder": False,
                    "model_breakdown": False,
                    "telegram_alerts": False,
                    "bankroll_tools": False,
                    "csv_upload": False,
                    "priority_support": False,
                },
            },
            {
                "name": "pro",
                "display_name": "Pro",
                "price_monthly": 49.0,
                "price_yearly": 490.0,
                "prediction_limit": 100,
                "features": {
                    "predictions": True,
                    "basic_history": True,
                    "advanced_analytics": True,
                    "ai_insights": True,
                    "accumulator_builder": True,
                    "model_breakdown": True,
                    "telegram_alerts": True,
                    "bankroll_tools": True,
                    "csv_upload": False,
                    "priority_support": False,
                },
            },
            {
                "name": "elite",
                "display_name": "Elite",
                "price_monthly": 199.0,
                "price_yearly": 1990.0,
                "prediction_limit": 1000,
                "features": {
                    "predictions": True,
                    "basic_history": True,
                    "advanced_analytics": True,
                    "ai_insights": True,
                    "accumulator_builder": True,
                    "model_breakdown": True,
                    "telegram_alerts": True,
                    "bankroll_tools": True,
                    "csv_upload": True,
                    "priority_support": True,
                    "validator_eligibility": True,
                    "revenue_share": True,
                },
            },
        ]

        async with AsyncSessionLocal() as _db:
            _count = (await _db.execute(_select(func.count()).select_from(SubscriptionPlan))).scalar()
            if _count == 0:
                for _p in _plans:
                    _db.add(SubscriptionPlan(
                        name=_p["name"],
                        display_name=_p["display_name"],
                        price_monthly=_p["price_monthly"],
                        price_yearly=_p["price_yearly"],
                        prediction_limit=_p["prediction_limit"],
                        features=_p["features"],
                        is_active=True,
                    ))
                await _db.commit()
                print("✅ Subscription plans seeded (Free / Pro / Elite)")
            else:
                print(f"✅ Subscription plans: {_count} already seeded")
    except Exception as _e:
        print(f"⚠️  Subscription plan seeding failed: {_e}")

    # BACKFILL WALLETS FOR EXISTING USERS
    try:
        import uuid as _uuid
        from decimal import Decimal as _Decimal
        from app.db.database import AsyncSessionLocal
        from app.db.models import User as _User
        from app.modules.wallet.models import Wallet as _Wallet
        from sqlalchemy import select as _select

        async with AsyncSessionLocal() as _db:
            _users = (await _db.execute(_select(_User))).scalars().all()
            _created = 0
            for _u in _users:
                _existing_wallet = (await _db.execute(
                    _select(_Wallet).where(_Wallet.user_id == _u.id)
                )).scalar_one_or_none()
                if not _existing_wallet:
                    _db.add(_Wallet(
                        id=str(_uuid.uuid4()),
                        user_id=_u.id,
                        vitcoin_balance=_Decimal("100.00000000"),
                    ))
                    _created += 1
            if _created:
                await _db.commit()
                print(f"✅ Wallets backfilled for {_created} existing user(s)")
    except Exception as _e:
        print(f"⚠️  Wallet backfill failed: {_e}")

    # ENFORCE ADMIN_PASSWORD — if ADMIN_PASSWORD env var is set, update any admin
    # whose password does not meet the current strength requirements.
    # Legacy hardcoded password strings have been removed from source code.
    # Set ADMIN_PASSWORD in your environment to rotate all admin credentials.
    try:
        import os as _os
        from app.db.database import AsyncSessionLocal
        from app.db.models import User as _User
        from app.auth.jwt_utils import hash_password, verify_password
        from sqlalchemy import select as _select
        import re as _re

        _secure_pass = _os.environ.get("ADMIN_PASSWORD", "")

        def _is_weak(hashed: str) -> bool:
            """Heuristic: short bcrypt hash cost (<= 10) = likely a legacy default."""
            try:
                cost = int(hashed.split("$")[2]) if hashed.startswith("$2") else 99
                return cost < 10
            except Exception:
                return False

        if _secure_pass:
            _strength_ok = (
                len(_secure_pass) >= 10
                and _re.search(r"[A-Z]", _secure_pass)
                and _re.search(r"[0-9]", _secure_pass)
                and _re.search(r"[^A-Za-z0-9]", _secure_pass)
            )
            if not _strength_ok:
                print("⚠️  ADMIN_PASSWORD does not meet strength requirements (10+ chars, uppercase, digit, special)")
            else:
                async with AsyncSessionLocal() as _db:
                    _admins = (await _db.execute(_select(_User).where(_User.role == "admin"))).scalars().all()
                    _updated = 0
                    for _admin in _admins:
                        if _is_weak(_admin.hashed_password):
                            _admin.hashed_password = hash_password(_secure_pass)
                            _updated += 1
                    if _updated:
                        await _db.commit()
                        print(f"✅ Rotated {_updated} admin account(s) to use ADMIN_PASSWORD from environment")
    except Exception as _e:
        print(f"⚠️  Admin password check failed: {_e}")

    # SEED VITCOIN INITIAL PRICE — ensure price history exists
    try:
        from decimal import Decimal as _Decimal
        from app.db.database import AsyncSessionLocal
        from app.modules.wallet.models import VITCoinPriceHistory
        from sqlalchemy import select as _select, func as _func

        async with AsyncSessionLocal() as _db:
            _price_count = (await _db.execute(_select(_func.count()).select_from(VITCoinPriceHistory))).scalar()
            if _price_count == 0:
                _db.add(VITCoinPriceHistory(
                    price_usd=_Decimal("0.10"),
                    circulating_supply=_Decimal("1000000"),
                    rolling_revenue_usd=_Decimal("0"),
                ))
                await _db.commit()
                print("✅ VITCoin initial price seeded: $0.10 USD")
            else:
                # One-shot heal: previous seed used $1.00 which disagreed with the
                # conversion engine's default ($0.10). Realign so the displayed
                # price matches what users actually receive on conversion.
                from app.modules.wallet.models import PlatformConfig as _PC2
                _floor_row = (await _db.execute(
                    _select(_PC2).where(_PC2.key == "vitcoin_price_floor")
                )).scalar_one_or_none()
                _floor_amt = _Decimal("0.10")
                if _floor_row and isinstance(_floor_row.value, dict):
                    try:
                        _floor_amt = _Decimal(str(_floor_row.value.get("amount", "0.10")))
                    except Exception:
                        pass
                from sqlalchemy import update as _update
                _stale = (await _db.execute(
                    _select(_func.count()).select_from(VITCoinPriceHistory).where(
                        VITCoinPriceHistory.price_usd >= _Decimal("1.00")
                    )
                )).scalar() or 0
                if _stale > 0 and _floor_amt < _Decimal("1.00"):
                    await _db.execute(
                        _update(VITCoinPriceHistory)
                        .where(VITCoinPriceHistory.price_usd >= _Decimal("1.00"))
                        .values(price_usd=_floor_amt)
                    )
                    await _db.commit()
                    print(f"✅ VITCoin price history: realigned {_stale} stale row(s) to ${_floor_amt}")
                else:
                    print(f"✅ VITCoin price history: {_price_count} record(s) present")
    except Exception as _e:
        print(f"⚠️  VITCoin price seeding failed: {_e}")

    # SEED SYNTHETIC MATCHES — populate if Match table is empty
    try:
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        from app.db.database import AsyncSessionLocal
        from app.db.models import Match as _Match
        from sqlalchemy import select as _select, func as _func

        async with AsyncSessionLocal() as _db:
            _match_count = (await _db.execute(_select(_func.count()).select_from(_Match))).scalar()
            if _match_count == 0:
                _now = _dt.now(_tz.utc)
                _tomorrow = _now + _td(days=1)
                _synthetic = [
                    ("premier_league",  "Premier League",    [("Arsenal", "Manchester City", 2.20, 3.40, 3.30), ("Liverpool", "Chelsea", 1.85, 3.60, 4.20), ("Manchester United", "Tottenham", 2.10, 3.50, 3.40), ("Newcastle", "Brighton", 2.40, 3.20, 2.90)]),
                    ("la_liga",         "La Liga",           [("Real Madrid", "Barcelona", 2.50, 3.30, 2.70), ("Atletico Madrid", "Sevilla", 1.75, 3.50, 4.50), ("Valencia", "Villarreal", 2.30, 3.30, 3.00)]),
                    ("bundesliga",      "Bundesliga",        [("Bayern Munich", "Borussia Dortmund", 1.65, 3.80, 5.50), ("RB Leipzig", "Bayer Leverkusen", 2.60, 3.20, 2.70), ("Eintracht Frankfurt", "Wolfsburg", 2.10, 3.30, 3.50)]),
                    ("serie_a",         "Serie A",           [("Inter Milan", "AC Milan", 2.10, 3.30, 3.40), ("Juventus", "Napoli", 2.30, 3.20, 3.00), ("Roma", "Lazio", 2.20, 3.30, 3.20)]),
                    ("ligue_1",         "Ligue 1",           [("Paris Saint-Germain", "Marseille", 1.55, 4.00, 6.50), ("Lyon", "Monaco", 2.40, 3.20, 2.80), ("Lille", "Rennes", 2.60, 3.10, 2.70)]),
                    ("eredivisie",      "Eredivisie",        [("Ajax", "PSV Eindhoven", 2.00, 3.40, 3.60), ("Feyenoord", "AZ Alkmaar", 1.90, 3.50, 4.00)]),
                    ("primeira_liga",   "Primeira Liga",     [("Benfica", "Porto", 2.20, 3.30, 3.10), ("Sporting CP", "Braga", 1.80, 3.50, 4.20)]),
                ]
                _added = 0
                for _day_offset, (_league_key, _league_name, _fixtures) in enumerate(_synthetic):
                    for _fi, (_home, _away, _oh, _od, _oa) in enumerate(_fixtures):
                        _kickoff = (_tomorrow + _td(days=_day_offset * 2, hours=14 + _fi * 3)).replace(tzinfo=None)
                        _ext_id = f"seed_{_league_key}_{_day_offset}_{_fi}"
                        _db.add(_Match(
                            external_id=_ext_id,
                            home_team=_home,
                            away_team=_away,
                            league=_league_key,
                            kickoff_time=_kickoff,
                            status="upcoming",
                            opening_odds_home=_oh,
                            opening_odds_draw=_od,
                            opening_odds_away=_oa,
                        ))
                        _added += 1
                await _db.commit()
                print(f"✅ Synthetic fixtures seeded: {_added} upcoming matches across 7 leagues")
            else:
                print(f"✅ Matches: {_match_count} fixture(s) already in database")
    except Exception as _e:
        print(f"⚠️  Synthetic match seeding failed: {_e}")

    # SERVICES
    orchestrator = get_orchestrator()
    if orchestrator:
        print(f"✅ ML Models: {orchestrator.num_models_ready()} ready")

    # E1 — Bootstrap model registry
    try:
        from app.db.database import AsyncSessionLocal
        from app.modules.ai.registry import bootstrap_registry
        async with AsyncSessionLocal() as _db:
            inserted = await bootstrap_registry(_db, orchestrator)
            print(f"✅ AI Model Registry: {inserted} new entries bootstrapped")
    except Exception as _e:
        print(f"⚠️  AI Registry bootstrap failed: {_e}")

    alerts = get_telegram_alerts()
    if alerts and alerts.enabled:
        await alerts.send_startup_message()

    supervised_tasks = [
        ("etl-pipeline", etl_pipeline_loop),
        ("odds-refresh", odds_refresh_loop),
        ("cache-purge", lambda: cache_background_purge_loop(300)),
    ]
    supervisor = BackgroundTaskSupervisor(
        supervised_tasks,
        check_interval=int(get_env("BACKGROUND_TASK_CHECK_INTERVAL_SECONDS", "30")),
        max_restarts=int(get_env("BACKGROUND_TASK_MAX_RESTARTS", "5")),
    )
    supervisor.start()
    app.state.background_supervisor = supervisor

    from app.services.exchange_rate import start_rate_refresh_loop
    tasks = [
        asyncio.create_task(auto_settle_loop(), name="auto-settle"),
        asyncio.create_task(live_match_tracker_loop(), name="live-match-tracker"),
        asyncio.create_task(model_accountability_loop(), name="model-accountability"),
        asyncio.create_task(vitcoin_pricing_loop(), name="vitcoin-pricing"),
        asyncio.create_task(subscription_expiry_loop(), name="subscription-expiry"),
        asyncio.create_task(start_rate_refresh_loop(), name="exchange-rate-oracle"),
    ]

    print("✅ Background services started with supervision")
    print("🌐 API running at http://localhost:5000")

    yield

    await supervisor.stop()
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    print("🛑 Shutdown complete")


# ============================================
# APP INIT
# ============================================

app = FastAPI(
    title="VIT Sports Intelligence Network",
    version=APP_VERSION,
    lifespan=lifespan,
)

# ============================================
# MIDDLEWARE
# ============================================

cors_origins = get_env("CORS_ALLOWED_ORIGINS", "*")
origins = ["*"] if cors_origins == "*" else cors_origins.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(APIKeyMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = (
        request.headers.get("X-Request-ID")
        or request.headers.get("X-Correlation-ID")
        or str(uuid.uuid4())
    )
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        logging.getLogger("app.errors").exception(
            "Unhandled request failure request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )
        raise
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Correlation-ID"] = request_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logging.getLogger("app.errors").warning(
        "Application error request_id=%s status=%s code=%s method=%s path=%s message=%s",
        getattr(request.state, "request_id", "unknown"),
        exc.status_code,
        exc.code,
        request.method,
        request.url.path,
        exc.message,
    )
    return error_response(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "HTTP error"
    logging.getLogger("app.errors").warning(
        "HTTP error request_id=%s status=%s method=%s path=%s detail=%s",
        getattr(request.state, "request_id", "unknown"),
        exc.status_code,
        request.method,
        request.url.path,
        detail,
    )
    return error_response(
        request=request,
        status_code=exc.status_code,
        code="http_error",
        message=detail,
        details=None if isinstance(exc.detail, str) else exc.detail,
        headers=dict(exc.headers or {}),
    )


def _sanitize_validation_errors(errors: list) -> list:
    """Convert any non-JSON-serializable objects in Pydantic error dicts to strings."""
    sanitized = []
    for err in errors:
        clean = {}
        for k, v in err.items():
            if k == "ctx" and isinstance(v, dict):
                clean[k] = {ck: str(cv) if not isinstance(cv, (str, int, float, bool, type(None))) else cv
                            for ck, cv in v.items()}
            elif isinstance(v, (str, int, float, bool, list, dict, type(None))):
                clean[k] = v
            else:
                clean[k] = str(v)
        sanitized.append(clean)
    return sanitized


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
    logging.getLogger("app.errors").exception(
        "Unhandled exception request_id=%s method=%s path=%s",
        getattr(request.state, "request_id", "unknown"),
        request.method,
        request.url.path,
    )
    return error_response(
        request=request,
        status_code=500,
        code="internal_server_error",
        message="Internal server error",
    )


# ============================================
# ROUTES
# ============================================

# Core
app.include_router(predict.router)
app.include_router(result.router)
app.include_router(history.router)
app.include_router(matches_route.router)
app.include_router(admin.router)
app.include_router(training_route.router)
app.include_router(analytics_route.router)
app.include_router(odds_route.router)
app.include_router(ai_feed.router)
app.include_router(ai_route.router)
app.include_router(subscription_route.router)
app.include_router(audit_route.router)
app.include_router(config_route.router)

# Auth (JWT)
app.include_router(auth_router)

# Wallet (Phase 1)
app.include_router(wallet_router)
app.include_router(wallet_admin_router)
app.include_router(webhooks_router)

# Blockchain (Phase 4)
app.include_router(blockchain_router)
app.include_router(oracle_router)

# Training Module (Module D)
app.include_router(training_module_router)

# AI Orchestration (Module E)
app.include_router(ai_engine_router)

# Dashboard
app.include_router(dashboard_router)

# Data Pipeline (Module F)
app.include_router(pipeline_router)

# Notifications (Module K)
app.include_router(notifications_router)
app.include_router(notifications_ws_router)

# Marketplace (Module G)
app.include_router(marketplace_router)

# Trust & Anti-Fraud (Module I)
app.include_router(trust_router)

# Cross-Chain Bridge (Module J)
app.include_router(bridge_router)

# Developer Platform (Module L)
app.include_router(developer_router)

# Governance (Module M)
app.include_router(governance_router)

# New features
app.include_router(verification_router)
app.include_router(totp_router)
app.include_router(referral_router)
app.include_router(leaderboard_router)
app.include_router(exports_router)


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
        .limit(10)
    )).all()
    ticker = []
    for match, prediction, clv in prediction_rows:
        edge = prediction.vig_free_edge if prediction.vig_free_edge is not None else prediction.raw_edge
        confidence = prediction.confidence or prediction.consensus_prob or 0
        if confidence <= 1:
            confidence *= 100
        ticker.append({
            "match": f"{match.home_team} vs {match.away_team}",
            "edge": f"{edge * 100:+.1f}%" if edge is not None else "—",
            "outcome": (clv.bet_outcome or "pending").upper() if clv else "PENDING",
            "confidence": round(confidence),
        })

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

    orchestrator = get_orchestrator()
    status = orchestrator.get_model_status() if orchestrator else {"models": [], "total": 0, "ready": 0}
    model_rows = []
    for model in status.get("models", [])[:6]:
        raw_confidence = model.get("accuracy") or model.get("accuracy_score") or model.get("confidence") or model.get("weight") or 0
        confidence = float(raw_confidence or 0)
        if confidence <= 1:
            confidence *= 100
        model_rows.append({
            "name": model.get("display_name") or model.get("name") or model.get("key") or model.get("model_key") or "Model",
            "confidence": round(confidence, 1),
            "weight": model.get("weight") or model.get("current_weight") or 0,
            "ready": bool(model.get("ready", model.get("loaded", False))),
            "trained_count": model.get("trained_count") or model.get("training_samples") or 0,
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
            "cta": "Start Free" if name == "free" else f"Go {plan.get('display_name', name.title())}",
            "highlight": name == "pro",
        })

    accuracy_rate = round((settled_wins / settled_total) * 100) if settled_total else 0
    return {
        "stats": {
            "predictions": total_predictions,
            "predictions_display": _format_count(total_predictions),
            "accuracy_rate": accuracy_rate,
            "accuracy_display": f"{accuracy_rate}%" if settled_total else "Live",
            "total_staked": float(total_staked),
            "total_staked_display": _format_money(float(total_staked)),
            "ai_models": status.get("total", 12),
            "ai_models_ready": status.get("ready", len(model_rows)),
        },
        "ticker": ticker,
        "testimonials": testimonials,
        "model_consensus": {
            "models": model_rows,
            "average_confidence": round(sum(m["confidence"] for m in model_rows) / len(model_rows), 1) if model_rows else 0,
        },
        "plans": plans,
    }


# ============================================
# UTILITIES
# ============================================

# ============================================
# HEALTH
# ============================================

@app.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)):
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except:
        db_ok = False

    orch = get_orchestrator()
    models = orch.num_models_ready() if orch else 0

    return HealthResponse(
        status="ok" if db_ok and models > 0 else "degraded",
        models_loaded=models,
        db_connected=db_ok,
        clv_tracking_enabled=True,
    )


@app.get("/system/status")
async def system_status(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = True
    except:
        db_status = False

    orch = get_orchestrator()
    loader = get_data_loader()

    # User stats
    from app.db.models import User, Prediction, CLVEntry
    from app.modules.wallet.models import Wallet, WalletTransaction
    from decimal import Decimal
    import datetime

    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    active_30d = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
    )).scalar() or 0
    validators = (await db.execute(
        select(func.count(User.id)).where(User.role == "validator")
    )).scalar() or 0

    # Economy stats
    total_staked_vit = Decimal("0")
    total_profit = Decimal("0")
    platform_volume = Decimal("0")
    try:
        total_staked_vit = (await db.execute(
            select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where(
                WalletTransaction.type == "stake"
            )
        )).scalar() or Decimal("0")
        platform_volume = (await db.execute(
            select(func.coalesce(func.sum(WalletTransaction.amount), 0))
        )).scalar() or Decimal("0")
        profit_result = (await db.execute(select(func.coalesce(func.sum(CLVEntry.profit), 0)))).scalar()
        total_profit = profit_result or Decimal("0")
    except Exception:
        pass

    return {
        "status": "operational",
        "version": APP_VERSION,
        "components": {
            "database": db_status,
            "models": orch.num_models_ready() if orch else 0,
            "data_pipeline": bool(loader),
        },
        "users": {
            "total": total_users,
            "active_30d": active_30d,
            "validators": validators,
        },
        "economy": {
            "total_staked_vit": float(total_staked_vit),
            "total_profit": float(total_profit),
            "platform_volume": float(platform_volume),
        },
    }


# ============================================
# FRONTEND — SPA + STATIC ASSETS
# ============================================

_FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if os.path.exists(_FRONTEND_DIST):
    # Serve compiled JS/CSS bundles
    _assets_dir = os.path.join(_FRONTEND_DIST, "assets")
    if os.path.exists(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    # Serve individual root-level static files
    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon():
        return FileResponse(os.path.join(_FRONTEND_DIST, "favicon.svg"))

    @app.get("/icons.svg", include_in_schema=False)
    async def icons_svg():
        return FileResponse(os.path.join(_FRONTEND_DIST, "icons.svg"))

    # SPA catch-all: serve index.html for every non-API path so React Router works
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Try serving a real file first (e.g. public assets)
        file_path = os.path.join(_FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # Fall back to index.html for client-side routing
        return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))
else:
    @app.get("/", include_in_schema=False)
    async def root_fallback():
        return {
            "name": "VIT Sports Intelligence Network",
            "version": APP_VERSION,
            "status": "live — frontend not built",
        }


# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 5000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )