"""Public configuration endpoint.

Single source of truth for values previously hardcoded in the frontend
(currencies, deposit presets, league/bookmaker labels, plan order,
governance categories, welcome bonus amount, model count, FX rates, etc.).

Cached briefly per process to avoid hammering the DB on every page load.
"""
from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Match
from app.modules.wallet.models import PlatformConfig
from app.api.routes.subscription import PLANS

router = APIRouter(prefix="/config", tags=["config"])

_CACHE: Dict[str, Any] = {"data": None, "ts": 0.0}
_CACHE_TTL_SECONDS = 60.0

# Friendly display labels — kept here so frontend never invents them.
CURRENCY_META = {
    "NGN":     {"symbol": "₦",   "label": "Nigerian Naira", "decimals": 2},
    "USD":     {"symbol": "$",   "label": "US Dollar",      "decimals": 2},
    "USDT":    {"symbol": "₮",   "label": "Tether",         "decimals": 2},
    "PI":      {"symbol": "π",   "label": "Pi Network",     "decimals": 4},
    "VITCoin": {"symbol": "VIT", "label": "VITCoin",        "decimals": 4},
}

DEPOSIT_PRESETS = {
    "NGN":     [5000, 10000, 25000, 50000, 100000],
    "USD":     [10, 25, 50, 100, 250],
    "USDT":    [10, 25, 50, 100, 250],
    "PI":      [10, 25, 50, 100, 250],
    "VITCoin": [100, 500, 1000, 2500, 5000],
}

GOVERNANCE_CATEGORIES = [
    {"id": "general",            "label": "General"},
    {"id": "fee_change",         "label": "Fee Change"},
    {"id": "parameter_update",   "label": "Parameter Update"},
    {"id": "feature_approval",   "label": "Feature Approval"},
]

# Bookmaker codes returned by the Odds API → human-readable labels.
BOOKMAKER_LABELS = {
    "pinnacle":      "Pinnacle",
    "bet365":        "bet365",
    "williamhill":   "William Hill",
    "betfair":       "Betfair",
    "unibet":        "Unibet",
    "betway":        "Betway",
    "draftkings":    "DraftKings",
    "fanduel":       "FanDuel",
    "1xbet":         "1xBet",
    "betsson":       "Betsson",
    "marathonbet":   "Marathon Bet",
    "888sport":      "888sport",
    "betvictor":     "Bet Victor",
    "ladbrokes":     "Ladbrokes",
    "coral":         "Coral",
    "skybet":        "Sky Bet",
}

# Short codes for league chips in the UI.
LEAGUE_SHORT = {
    "premier_league":         "EPL",
    "la_liga":                "LL",
    "bundesliga":             "BL",
    "serie_a":                "SA",
    "ligue_1":                "L1",
    "championship":           "CH",
    "eredivisie":             "ED",
    "primeira_liga":          "PL",
    "scottish_premiership":   "SP",
    "belgian_pro_league":     "BPL",
    "champions_league":       "UCL",
    "europa_league":          "UEL",
    "world_cup":              "WC",
}

PLAN_FEATURE_LABELS = {
    "predictions":          "AI predictions",
    "basic_history":        "Match history",
    "advanced_analytics":   "Advanced analytics",
    "ai_insights":          "AI insights & explanations",
    "accumulator_builder":  "Accumulator builder",
    "model_breakdown":      "Per-model breakdown",
    "telegram_alerts":      "Telegram alerts",
    "bankroll_tools":       "Bankroll & staking tools",
    "csv_upload":           "CSV upload",
    "priority_support":     "Priority support",
    "submit_predictions":   "Submit predictions to pool",
    "validator_rewards":    "Validator pool rewards",
    "governance_voting":    "Governance voting",
    "over_under":           "Over/Under markets",
    "btts":                 "Both teams to score",
    "asian_handicap":       "Asian handicap",
}


async def _get_kv(db: AsyncSession, key: str, default):
    row = (await db.execute(select(PlatformConfig).where(PlatformConfig.key == key))).scalar_one_or_none()
    if not row:
        return default
    val = row.value
    if val is None:
        return default
    return val


async def _build_config(db: AsyncSession) -> Dict[str, Any]:
    # FX rates — read from PlatformConfig with sensible fallbacks (same source
    # as /wallet/exchange-rates, deliberately duplicated lightly to avoid
    # cross-module deps in the public-config path).
    ngn_usd_rate = float(await _get_kv(db, "ngn_usd_rate", 0.000633) or 0.000633)
    pi_usd_rate  = float(await _get_kv(db, "pi_usd_rate",  0.314159) or 0.314159)
    welcome_bonus_vit = int(float(await _get_kv(db, "welcome_bonus_vit", 100) or 100))

    # Live VIT price — best-effort (avoid importing the wallet module here).
    vit_usd = 0.10
    try:
        from app.modules.wallet.pricing import VITCoinPricingEngine
        prices = await VITCoinPricingEngine(db).get_current_price()
        vit_usd = float(prices.get("usd", vit_usd))
    except Exception:
        pass

    # Distinct leagues actually present in the DB → real, not invented.
    league_rows = (await db.execute(
        select(Match.league).where(Match.league.is_not(None)).distinct()
    )).scalars().all()
    leagues = []
    seen = set()
    for raw in league_rows:
        if not raw:
            continue
        key = raw.strip().lower().replace(" ", "_")
        if key in seen:
            continue
        seen.add(key)
        leagues.append({
            "id":         key,
            "raw":        raw,
            "label":      raw.replace("_", " ").title(),
            "short":      LEAGUE_SHORT.get(key, raw[:3].upper()),
        })
    leagues.sort(key=lambda x: x["label"])

    # Model count — pulled from the AI orchestrator if possible.
    model_count = 12
    try:
        from app.modules.ai.orchestrator import ENSEMBLE_MODELS  # type: ignore
        model_count = len(ENSEMBLE_MODELS)
    except Exception:
        try:
            from app.modules.ai.orchestrator import get_orchestrator
            model_count = len(getattr(get_orchestrator(), "models", []) or []) or model_count
        except Exception:
            pass

    plan_order = ["free", "analyst", "pro", "validator", "elite"]
    # Filter to plans that actually exist in PLANS (drops "elite" if undefined).
    plan_order = [p for p in plan_order if p in PLANS]

    return {
        "currencies": [
            {"code": code, **meta}
            for code, meta in CURRENCY_META.items()
        ],
        "deposit_presets":   DEPOSIT_PRESETS,
        "leagues":           leagues,
        "league_short":      LEAGUE_SHORT,
        "bookmaker_labels":  BOOKMAKER_LABELS,
        "plan_order":        plan_order,
        "plan_feature_labels": PLAN_FEATURE_LABELS,
        "governance_categories": GOVERNANCE_CATEGORIES,
        "fx": {
            "ngn_usd_rate":   ngn_usd_rate,
            "ngn_per_usd":    round(1.0 / ngn_usd_rate, 2) if ngn_usd_rate > 0 else 1580.0,
            "pi_usd_rate":    pi_usd_rate,
            "vit_usd":        vit_usd,
        },
        "platform": {
            "welcome_bonus_vit": welcome_bonus_vit,
            "model_count":       model_count,
            "version":           "4.0.0",
        },
    }


@router.get("/public")
async def public_config(db: AsyncSession = Depends(get_db)):
    """Single source of truth for values the frontend used to hardcode.

    Cached for 60s per process. Safe to call without auth.
    """
    now = time.time()
    if _CACHE["data"] is not None and (now - _CACHE["ts"]) < _CACHE_TTL_SECONDS:
        return _CACHE["data"]
    data = await _build_config(db)
    _CACHE["data"] = data
    _CACHE["ts"] = now
    return data


@router.post("/public/refresh")
async def refresh_public_config(db: AsyncSession = Depends(get_db)):
    """Force-refresh the cache (admin convenience)."""
    _CACHE["data"] = None
    return await public_config(db)
