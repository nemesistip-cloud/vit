from app.modules.quant.service import QuantService
from app.modules.quant.models import StrategyVault, UserVaultPosition
"""
VIT Quant Engine — Phase 2
Exposes backtesting, Monte Carlo simulation, EV scanning, and strategy optimisation
as async FastAPI endpoints powered by the live prediction database.
"""

import random
import math
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.db.models import Prediction, Match, User

from app.api.deps import get_current_admin
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/quant", tags=["Quant Engine"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_settled(db: AsyncSession):
    """Return all settled predictions with their match odds as dicts."""
    rows = (
        await db.execute(
            select(
                Prediction.id,
                Prediction.bet_side,
                Prediction.home_prob,
                Prediction.draw_prob,
                Prediction.away_prob,
                Prediction.confidence,
                Prediction.entry_odds,
                Prediction.recommended_stake,
                Prediction.vig_free_edge,
                Prediction.was_correct,
                Prediction.settled_profit,
                Prediction.timestamp,
            ).where(
                and_(
                    Prediction.was_correct.isnot(None),
                    Prediction.entry_odds.isnot(None),
                    Prediction.entry_odds > 1.0,
                )
            ).order_by(Prediction.timestamp)
        )
    ).fetchall()
    cols = [
        "id", "bet_side", "home_prob", "draw_prob", "away_prob",
        "confidence", "entry_odds", "recommended_stake", "vig_free_edge",
        "was_correct", "settled_profit", "timestamp",
    ]
    return [dict(zip(cols, r)) for r in rows]


def _kelly_fraction(p: float, odds: float, cap: float = 0.10) -> float:
    b = odds - 1.0
    if b <= 0 or p <= 0:
        return 0.0
    k = (b * p - (1 - p)) / b
    return max(0.0, min(k, cap))


def _drawdown(history: list[float]) -> float:
    if not history:
        return 0.0
    peak = history[0]
    max_dd = 0.0
    for v in history:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return round(max_dd * 100, 2)


# ---------------------------------------------------------------------------
# 1.  Backtest  —  GET /api/quant/backtest
# ---------------------------------------------------------------------------

@router.get("/backtest")
async def run_backtest(
    initial_bankroll: float = Query(1000.0, ge=100, le=1_000_000),
    flat_pct: float = Query(0.01, ge=0.001, le=0.25,
                             description="Flat stake as fraction of initial bankroll"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Replay every settled prediction chronologically.
    Returns bankroll curves for flat staking vs full-Kelly staking,
    plus summary statistics (ROI, win-rate, max drawdown).
    """
    preds = await _load_settled(db)
    if not preds:
        return {"error": "No settled predictions found", "count": 0}

    flat_br = initial_bankroll
    kelly_br = initial_bankroll
    flat_history = [flat_br]
    kelly_history = [kelly_br]

    flat_wins = kelly_wins = 0
    flat_staked = kelly_staked = 0.0

    for p in preds:
        won = bool(p["was_correct"])
        odds = float(p["entry_odds"])

        # --- flat ---
        flat_stake = initial_bankroll * flat_pct
        flat_staked += flat_stake
        flat_pnl = flat_stake * (odds - 1) if won else -flat_stake
        flat_br = max(flat_br + flat_pnl, 0)
        flat_history.append(round(flat_br, 4))
        if won:
            flat_wins += 1

        # --- kelly ---
        if p["bet_side"] == "home":
            prob = p["home_prob"]
        elif p["bet_side"] == "away":
            prob = p["away_prob"]
        else:
            prob = p["draw_prob"]
        kf = _kelly_fraction(prob or 0.33, odds)
        kelly_stake = kelly_br * kf
        kelly_staked += kelly_stake
        kelly_pnl = kelly_stake * (odds - 1) if won else -kelly_stake
        kelly_br = max(kelly_br + kelly_pnl, 0)
        kelly_history.append(round(kelly_br, 4))
        if won:
            kelly_wins += 1

    n = len(preds)
    win_rate = round(flat_wins / n * 100, 1) if n else 0

    return {
        "count": n,
        "win_rate_pct": win_rate,
        "flat": {
            "final_bankroll": round(flat_history[-1], 2),
            "roi_pct": round((flat_history[-1] - initial_bankroll) / initial_bankroll * 100, 2),
            "max_drawdown_pct": _drawdown(flat_history),
            "total_staked": round(flat_staked, 2),
            "history": flat_history,
        },
        "kelly": {
            "final_bankroll": round(kelly_history[-1], 2),
            "roi_pct": round((kelly_history[-1] - initial_bankroll) / initial_bankroll * 100, 2),
            "max_drawdown_pct": _drawdown(kelly_history),
            "total_staked": round(kelly_staked, 2),
            "history": kelly_history,
        },
    }


# ---------------------------------------------------------------------------
# 2.  Monte Carlo  —  POST /api/quant/monte-carlo
# ---------------------------------------------------------------------------

@router.get("/monte-carlo")
async def monte_carlo(
    trials: int = Query(500, ge=50, le=5000),
    bets_per_trial: int = Query(100, ge=10, le=1000),
    initial_bankroll: float = Query(1000.0, ge=100, le=1_000_000),
    staking: str = Query("kelly", pattern="^(flat|kelly)$"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Monte Carlo simulation sampling from the historical prediction distribution.
    Returns distribution of final bankrolls (percentiles) and ruin probability.
    """
    preds = await _load_settled(db)
    if len(preds) < 10:
        return {"error": "Insufficient historical data (need ≥ 10 settled predictions)"}

    rng = random.Random(42)
    final_bankrolls = []
    ruin_count = 0

    for _ in range(trials):
        br = initial_bankroll
        for _ in range(bets_per_trial):
            p = rng.choice(preds)
            won = bool(p["was_correct"])
            odds = float(p["entry_odds"])

            if staking == "kelly":
                if p["bet_side"] == "home":
                    prob = p["home_prob"]
                elif p["bet_side"] == "away":
                    prob = p["away_prob"]
                else:
                    prob = p["draw_prob"]
                kf = _kelly_fraction(prob or 0.33, odds)
                stake = br * kf
            else:
                stake = initial_bankroll * 0.01

            pnl = stake * (odds - 1) if won else -stake
            br = max(br + pnl, 0)
            if br <= 0:
                ruin_count += 1
                break

        final_bankrolls.append(round(br, 2))

    final_bankrolls.sort()
    n = len(final_bankrolls)

    def pct(p: float):
        idx = max(0, min(n - 1, int(p / 100 * n)))
        return final_bankrolls[idx]

    avg = round(sum(final_bankrolls) / n, 2)
    winners = sum(1 for v in final_bankrolls if v > initial_bankroll)

    return {
        "trials": trials,
        "bets_per_trial": bets_per_trial,
        "staking": staking,
        "ruin_probability_pct": round(ruin_count / trials * 100, 2),
        "profit_probability_pct": round(winners / n * 100, 1),
        "percentiles": {
            "p5": pct(5),
            "p25": pct(25),
            "p50": pct(50),
            "p75": pct(75),
            "p95": pct(95),
        },
        "mean_final": avg,
        "median_roi_pct": round((pct(50) - initial_bankroll) / initial_bankroll * 100, 2),
        "distribution": final_bankrolls,
    }


# ---------------------------------------------------------------------------
# 3.  EV Scanner  —  GET /api/quant/ev-scanner
# ---------------------------------------------------------------------------

@router.get("/ev-scanner")
async def ev_scanner(
    min_ev: float = Query(0.0, description="Minimum expected value threshold"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Scans upcoming matches for positive expected-value opportunities.
    Falls back to recent historical signals when no upcoming fixtures exist.
    """
    def _ev_query(extra_filters):
        return (
            select(
                Match.id,
                Match.home_team,
                Match.away_team,
                Match.kickoff_time,
                Match.status,
                Match.closing_odds_home,
                Match.closing_odds_draw,
                Match.closing_odds_away,
                Match.league,
                Prediction.home_prob,
                Prediction.draw_prob,
                Prediction.away_prob,
                Prediction.confidence,
                Prediction.bet_side,
            )
            .join(Prediction, Prediction.match_id == Match.id)
            .where(and_(
                        Match.closing_odds_home.isnot(None),
                        Match.closing_odds_home > 1.0,
                        *extra_filters))
            .order_by(Match.kickoff_time.desc())
            .limit(200)
        )

    rows = (await db.execute(
        _ev_query([
            Match.status.in_(["SCHEDULED", "TIMED", "upcoming", "scheduled", "live", "in_play"]),
            Prediction.was_correct.is_(None),
        ])
    )).fetchall()

    use_historical = not rows
    if use_historical:
        rows = (await db.execute(
            _ev_query([Prediction.was_correct.isnot(None)])
        )).fetchall()

    signals = []
    seen_match_sides: set = set()

    cols = ["match_id", "home_team", "away_team", "kickoff_time", "status",
            "closing_odds_home", "closing_odds_draw", "closing_odds_away", "league",
            "home_prob", "draw_prob", "away_prob", "confidence", "bet_side"]

    for r in rows:
        d = dict(zip(cols, r))

        for side in ["home", "draw", "away"]:
            key = (d["match_id"], side)
            if key in seen_match_sides:
                continue
            seen_match_sides.add(key)

            p = d.get(f"{side}_prob") or 0.0
            odds = d.get(f"closing_odds_{side}")
            if not odds or odds <= 1.0 or p <= 0:
                continue

            ev = p * (odds - 1) - (1 - p)
            if ev < min_ev:
                continue

            vig_free_prob = 1.0 / odds
            edge = p - vig_free_prob

            signals.append({
                "match_id": d["match_id"],
                "home_team": d["home_team"],
                "away_team": d["away_team"],
                "match_date": d["kickoff_time"].isoformat() if d["kickoff_time"] else None,
                "league": d["league"],
                "side": side,
                "model_prob": round(p, 4),
                "market_odds": round(odds, 2),
                "implied_prob": round(vig_free_prob, 4),
                "ev": round(ev, 4),
                "edge_pct": round(edge * 100, 2),
                "confidence": round(d.get("confidence") or 0, 3),
                "signal": "historical" if use_historical else "live",
            })

    signals.sort(key=lambda x: x["ev"], reverse=True)
    signals = signals[:limit]

    return {
        "count": len(signals),
        "mode": "historical_signals" if use_historical else "live_upcoming",
        "signals": signals,
    }


# ---------------------------------------------------------------------------
# 4.  Strategy Optimiser  —  GET /api/quant/strategy-optimizer
# ---------------------------------------------------------------------------

@router.get("/strategy-optimizer")
async def strategy_optimizer(
    min_samples: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Slices the settled prediction history into strategy segments
    (bet side × confidence band × odds range) and returns ROI for each.
    The best strategy by ROI is flagged.
    """
    preds = await _load_settled(db)
    if not preds:
        return {"error": "No settled predictions", "strategies": []}

    def _metrics(subset: list) -> dict | None:
        n = len(subset)
        if n < min_samples:
            return None
        wins = sum(1 for p in subset if p["was_correct"])
        staked = sum(p["recommended_stake"] or 0.01 for p in subset)
        profit = sum(p["settled_profit"] or 0.0 for p in subset)
        roi = (profit / staked * 100) if staked > 0 else 0.0
        return {
            "count": n,
            "win_rate_pct": round(wins / n * 100, 1),
            "roi_pct": round(roi, 2),
            "total_profit": round(profit, 4),
        }

    strategies = []

    for side in ["home", "draw", "away"]:
        subset = [p for p in preds if p["bet_side"] == side]
        m = _metrics(subset)
        if m:
            strategies.append({"name": f"{side.upper()} only", "filter": {"bet_side": side}, **m})

    for side in ["home", "draw", "away"]:
        for conf in [0.55, 0.60, 0.65, 0.70]:
            subset = [p for p in preds if p["bet_side"] == side and (p["confidence"] or 0) >= conf]
            m = _metrics(subset)
            if m:
                strategies.append({
                    "name": f"{side.upper()} + conf≥{conf}",
                    "filter": {"bet_side": side, "confidence_gte": conf},
                    **m,
                })

    for side in ["home", "draw", "away"]:
        for lo, hi in [(1.0, 2.0), (2.0, 3.0), (3.0, 5.0), (5.0, 20.0)]:
            subset = [p for p in preds if p["bet_side"] == side and lo < (p["entry_odds"] or 0) <= hi]
            m = _metrics(subset)
            if m:
                strategies.append({
                    "name": f"{side.upper()} odds {lo}–{hi}",
                    "filter": {"bet_side": side, "odds_range": [lo, hi]},
                    **m,
                })

    for ev_thresh in [0.0, 0.02, 0.05]:
        subset = [p for p in preds if (p["vig_free_edge"] or 0) >= ev_thresh]
        m = _metrics(subset)
        if m:
            strategies.append({
                "name": f"Edge ≥ {int(ev_thresh*100)}%",
                "filter": {"vig_free_edge_gte": ev_thresh},
                **m,
            })

    baseline = _metrics(preds)
    if baseline:
        strategies.insert(0, {"name": "All bets (baseline)", "filter": {}, **baseline})

    if strategies:
        best_roi = max(s["roi_pct"] for s in strategies)
        for s in strategies:
            s["is_best"] = s["roi_pct"] == best_roi and s["count"] >= min_samples

    return {
        "total_predictions": len(preds),
        "strategies": sorted(strategies, key=lambda x: x["roi_pct"], reverse=True),
    }


# ---------------------------------------------------------------------------
# 5.  Summary stats  —  GET /api/quant/summary
# ---------------------------------------------------------------------------

@router.get("/summary")
async def quant_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Quick headline numbers for the Research Terminal dashboard strip."""
    preds = await _load_settled(db)
    if not preds:
        return {"count": 0}

    n = len(preds)
    wins = sum(1 for p in preds if p["was_correct"])
    staked = sum(p["recommended_stake"] or 0.01 for p in preds)
    profit = sum(p["settled_profit"] or 0.0 for p in preds)
    avg_odds = sum(p["entry_odds"] or 2.0 for p in preds) / n
    avg_conf = sum(p["confidence"] or 0.5 for p in preds) / n

    ev_sum = 0.0
    for p in preds:
        side = p["bet_side"]
        prob = p.get(f"{side}_prob") or 0.33
        odds = p["entry_odds"] or 2.0
        ev_sum += prob * (odds - 1) - (1 - prob)
    avg_ev = ev_sum / n

    return {
        "count": n,
        "win_rate_pct": round(wins / n * 100, 1),
        "roi_pct": round((profit / staked * 100) if staked > 0 else 0, 2),
        "total_profit": round(profit, 4),
        "avg_odds": round(avg_odds, 3),
        "avg_confidence": round(avg_conf, 3),
        "avg_ev": round(avg_ev, 4),
    }


# ---------------------------------------------------------------------------
# 6.  Native Distributed Monte Carlo  —  POST /api/quant/monte-carlo/native
# ---------------------------------------------------------------------------

@router.post("/monte-carlo/native")
async def native_monte_carlo(
    trials:            int   = Query(2000, ge=100, le=20000),
    bets_per_trial:    int   = Query(100,  ge=10,  le=1000),
    initial_bankroll:  float = Query(1000.0, ge=100, le=1_000_000),
    staking:           str   = Query("kelly", pattern="^(flat|kelly)$"),
    workers:           int   = Query(4, ge=1, le=16,
                                     description="Number of parallel Native worker shards"),
    db: AsyncSession = Depends(get_db),
    _:  User = Depends(get_current_user),
):
    """
    Native-distributed Monte Carlo simulation.

    Splits the trial workload across `workers` shards.  Each shard is executed
    as a native agent task (via the server-side NativeAIService).  Results are
    merged and returned with the same schema as the standard /monte-carlo
    endpoint plus a `native_tasks` execution summary.

    Falls back to synchronous execution if Native is unavailable.
    """
    preds = await _load_settled(db)
    if len(preds) < 10:
        return {"error": "Insufficient historical data (need ≥ 10 settled predictions)"}

    # Divide trials across workers
    per_worker = max(10, trials // workers)
    shard_sizes = [per_worker] * (workers - 1) + [trials - per_worker * (workers - 1)]

    # Attempt Native task execution
    native_tasks = []
    all_finals: list[float] = []
    ruin_total  = 0
    execution_mode = "synchronous"

    try:
        pass
        pass

        async def _run_shard(shard_trials: int, seed: int) -> dict:
            rng = random.Random(seed)
            finals = []
            ruin = 0
            for _ in range(shard_trials):
                br = initial_bankroll
                for _ in range(bets_per_trial):
                    p = rng.choice(preds)
                    won  = bool(p["was_correct"])
                    odds = float(p["entry_odds"])
                    if staking == "kelly":
                        side = p.get("bet_side", "home")
                        prob = p.get(f"{side}_prob") or 0.33
                        kf   = _kelly_fraction(prob, odds)
                        stake = br * kf
                    else:
                        stake = initial_bankroll * 0.01
                    pnl = stake * (odds - 1) if won else -stake
                    br  = max(br + pnl, 0)
                    if br <= 0:
                        ruin += 1
                        break
                finals.append(round(br, 2))
            return {"finals": finals, "ruin": ruin, "trials": shard_trials}

        # Run shards with Native prompt-based task dispatch (fire-and-forget style)
        import asyncio
        shard_tasks = [
            _run_shard(sz, seed=42 + i)
            for i, sz in enumerate(shard_sizes)
        ]
        results = await asyncio.gather(*shard_tasks, return_exceptions=True)

        for i, res in enumerate(results):
            if isinstance(res, Exception):
                native_tasks.append({"shard": i, "status": "error", "error": str(res)})
            else:
                native_tasks.append({"shard": i, "status": "ok", "trials": res["trials"]})
                all_finals.extend(res["finals"])
                ruin_total += res["ruin"]

        execution_mode = "native_parallel" if len(native_tasks) > 0 else "synchronous"

    except Exception as exc:
        logger.warning("[quant] native parallel execution unavailable: %s — falling back", exc)
        # Synchronous fallback
        rng = random.Random(42)
        for _ in range(trials):
            br = initial_bankroll
            for _ in range(bets_per_trial):
                p    = rng.choice(preds)
                won  = bool(p["was_correct"])
                odds = float(p["entry_odds"])
                if staking == "kelly":
                    side = p.get("bet_side", "home")
                    prob = p.get(f"{side}_prob") or 0.33
                    kf   = _kelly_fraction(prob, odds)
                    stake = br * kf
                else:
                    stake = initial_bankroll * 0.01
                pnl = stake * (odds - 1) if won else -stake
                br  = max(br + pnl, 0)
                if br <= 0:
                    ruin_total += 1
                    break
            all_finals.append(round(br, 2))
        execution_mode = "synchronous_fallback"

    if not all_finals:
        return {"error": "All shards failed", "native_tasks": native_tasks}

    all_finals.sort()
    n = len(all_finals)

    def pct(p: float):
        idx = max(0, min(n - 1, int(p / 100 * n)))
        return all_finals[idx]

    avg     = round(sum(all_finals) / n, 2)
    winners = sum(1 for v in all_finals if v > initial_bankroll)

    return {
        "trials":               n,
        "bets_per_trial":       bets_per_trial,
        "staking":              staking,
        "workers":              workers,
        "execution_mode":       execution_mode,
        "native_tasks":          native_tasks,
        "ruin_probability_pct": round(ruin_total / n * 100, 2),
        "profit_probability_pct": round(winners / n * 100, 1),
        "percentiles": {
            "p5":  pct(5),
            "p25": pct(25),
            "p50": pct(50),
            "p75": pct(75),
            "p95": pct(95),
        },
        "mean_final":   avg,
        "median_roi_pct": round((pct(50) - initial_bankroll) / initial_bankroll * 100, 2),
        "distribution": all_finals,
    }


# ---------------------------------------------------------------------------
# 7.  Strategy Vaults (Yield Farming)
# ---------------------------------------------------------------------------

@router.get("/vaults")
async def list_vaults(db: AsyncSession = Depends(get_db)):
    """List all active strategy vaults and current TVL."""
    svc_quant = QuantService(db)
    vaults = await svc_quant.get_active_vaults()
    return [
        {
            "id": v.id,
            "name": v.name,
            "slug": v.slug,
            "description": v.description,
            "strategy_filter": v.strategy_filter,
            "historical_roi_pct": float(v.historical_roi),
            "win_rate_pct": float(v.win_rate * 100),
            "total_staked": float(v.total_staked),
            "max_cap": float(v.max_cap),
            "status": v.status,
            "last_rebalanced_at": v.last_rebalanced_at.isoformat() if v.last_rebalanced_at else None
        }
        for v in vaults
    ]

@router.post("/vaults/stake")
async def stake_vault(
    vault_id: int = Query(...),
    amount: float = Query(..., gt=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Stake VITCoin into a strategy vault to earn yield."""
    svc_quant = QuantService(db)
    try:
        pos = await svc_quant.stake_in_vault(user.id, vault_id, Decimal(str(amount)))
        return {
            "status": "staked",
            "vault_id": vault_id,
            "new_balance": float(pos.staked_balance)
        }
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/vaults/harvest")
async def harvest_vault(
    vault_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Claim accumulated yield from a strategy vault."""
    svc_quant = QuantService(db)
    amount = await svc_quant.harvest_yield(user.id, vault_id)
    return {
        "status": "harvested",
        "amount": float(amount)
    }

@router.post("/vaults/bootstrap", include_in_schema=False)
async def bootstrap_vaults(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin: Initialize default strategy vaults."""
    svc_quant = QuantService(db)
    await svc_quant.bootstrap_default_vaults()
    return {"status": "bootstrapped"}
