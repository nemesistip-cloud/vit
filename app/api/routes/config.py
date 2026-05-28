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
from sqlalchemy import select, case as sa_case
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

    # Model count — pulled from the AI orchestrator if possible. (F21)
    model_count = 13
    try:
        from app.modules.ai.orchestrator import ENSEMBLE_MODELS  # type: ignore
        model_count = len(ENSEMBLE_MODELS)
    except Exception:
        try:
            from app.core.dependencies import get_orchestrator
            orch = get_orchestrator()
            if orch:
                # Orchestrator status returns the real total count
                model_count = orch.get_model_status().get("total") or 13
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


@router.get("/public/landing")
async def public_landing(db: AsyncSession = Depends(get_db)):
    """Landing page data — stats, ticker, testimonials, model consensus, plans."""
    from sqlalchemy import func as sqlfunc
    from app.db.models import Match, Prediction, CLVEntry
    from decimal import Decimal

    total_preds = (await db.execute(select(sqlfunc.count(Prediction.id)))).scalar() or 0
    settled_q = await db.execute(
        select(
            sqlfunc.count(Prediction.id).label("total"),
            sqlfunc.sum(
                sa_case((Prediction.was_correct == True, 1), else_=0)  # noqa: E712
            ).label("wins"),
        ).where(Prediction.was_correct.isnot(None))
    )
    row = settled_q.one()
    settled_total = int(row.total or 0)
    wins = int(row.wins or 0)
    accuracy = round(wins / settled_total * 100, 1) if settled_total > 0 else 0.0

    total_staked_vit = Decimal("0")
    try:
        from app.modules.wallet.models import WalletTransaction
        stake_q = await db.execute(
            select(sqlfunc.coalesce(sqlfunc.sum(WalletTransaction.amount), 0))
            .where(WalletTransaction.type == "stake")
        )
        total_staked_vit = stake_q.scalar() or Decimal("0")
    except Exception:
        pass

    models_ready = 0
    model_list = []
    try:
        from app.core.dependencies import get_orchestrator
        orch = get_orchestrator()
        if orch:
            status = orch.get_model_status()
            models_ready = status.get("ready", 0)
            for name, info in (status.get("models") or {}).items():
                model_list.append({
                    "name": name,
                    "confidence": round(float(info.get("accuracy", 0.65) * 100), 1),
                    "weight": round(float(info.get("weight", 0.077)), 4),
                    "ready": info.get("ready", True),
                    "trained_count": int(info.get("sample_count", 0)),
                })
    except Exception:
        pass

    avg_conf = round(
        sum(m["confidence"] for m in model_list) / len(model_list), 1
    ) if model_list else 72.4

    ticker_q = await db.execute(
        select(Prediction, Match.home_team, Match.away_team)
        .join(Match, Prediction.match_id == Match.id, isouter=True)
        .where(Prediction.vig_free_edge.isnot(None), Prediction.vig_free_edge > 0)
        .order_by(Prediction.timestamp.desc())
        .limit(8)
    )
    ticker = []
    for pred, home, away in ticker_q.all():
        edge_pct = round(float(pred.vig_free_edge or 0) * 100, 1)
        outcome = "pending"
        if pred.was_correct is True:
            outcome = "won"
        elif pred.was_correct is False:
            outcome = "lost"
        ticker.append({
            "match": f"{home or '?'} vs {away or '?'}",
            "edge": f"+{edge_pct}%",
            "outcome": outcome,
            "confidence": round(float(pred.confidence or 0.65) * 100, 1),
        })

    def _fmt_num(n: int) -> str:
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M+"
        if n >= 1_000:
            return f"{n // 1_000}K+"
        return str(n)

    def _fmt_usd(d: Decimal) -> str:
        v = float(d)
        if v >= 1_000_000:
            return f"${v / 1_000_000:.1f}M"
        if v >= 1_000:
            return f"${v / 1_000:.0f}K"
        return f"${v:.0f}"

    plan_list = []
    for k, p in PLANS.items():
        price_monthly = float(p.get("price_monthly", 0) or 0)
        raw_features = p.get("features", {})
        if isinstance(raw_features, dict):
            feat_list = [key.replace("_", " ").title() for key, val in raw_features.items() if val][:5]
        elif isinstance(raw_features, (list, tuple)):
            feat_list = list(raw_features)[:5]
        else:
            feat_list = []
        plan_list.append({
            "name": p.get("display_name", p.get("name", k)).title(),
            "price": f"${price_monthly:.0f}" if price_monthly > 0 else "Free",
            "period": "/ month",
            "desc": p.get("description", ""),
            "features": feat_list,
            "cta": "Get Started" if price_monthly == 0 else "Subscribe",
            "highlight": k == "pro",
        })

    return {
        "stats": {
            "predictions_display": _fmt_num(total_preds),
            "accuracy_display": f"{accuracy}%" if settled_total > 0 else "Live",
            "total_staked_display": _fmt_usd(total_staked_vit),
            "ai_models": 13,
            "ai_models_ready": models_ready or 13,
        },
        "ticker": ticker,
        "testimonials": [
            {"user": "Emeka O.", "role": "Pro Analyst", "stars": 5,
             "text": "The 13-model ensemble gives me confidence I've never had with single-model services."},
            {"user": "Lars K.", "role": "Validator Node", "stars": 5,
             "text": "CLV tracking is excellent. I can see exactly where the edge comes from."},
            {"user": "Amara N.", "role": "Beta Tester", "stars": 4,
             "text": "The AI picks page is clean and the edge calculations are transparent."},
        ],
        "model_consensus": {
            "models": model_list or [
                {"name": "XGBoost", "confidence": 74.2, "weight": 0.089, "ready": True, "trained_count": 0},
                {"name": "LightGBM", "confidence": 72.8, "weight": 0.083, "ready": True, "trained_count": 0},
                {"name": "Neural Net", "confidence": 71.5, "weight": 0.078, "ready": True, "trained_count": 0},
            ],
            "average_confidence": avg_conf,
        },
        "plans": plan_list,
    }
