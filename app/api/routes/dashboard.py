"""Dashboard summary endpoints — all data properly scoped per user."""

import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import CLVEntry, Match, Prediction, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

# In-process price cache
_price_cache = {
    "data": None,
    "timestamp": None
}

async def _settled_predictions_for_user(db: AsyncSession, uid: int):
    rows = await db.execute(
        select(Prediction.bet_side, Match.actual_outcome, Match.kickoff_time)
        .join(Match, Match.id == Prediction.match_id)
        .where(Prediction.user_id == uid)
        .where(Prediction.bet_side.isnot(None))
        .where(Match.actual_outcome.isnot(None))
        .order_by(Match.kickoff_time.desc())
    )
    return rows.all()


def _wins_settled_streak(rows) -> tuple[int, int, int]:
    settled = 0
    wins = 0
    streak = 0
    streak_locked = False
    for bet_side, outcome, _ in rows:
        if not bet_side or not outcome:
            continue
        settled += 1
        won = str(bet_side).lower() == str(outcome).lower()
        if won:
            wins += 1
            if not streak_locked:
                streak += 1
        else:
            streak_locked = True
    return wins, settled, streak


@router.get("")
@router.get("/summary")
async def get_dashboard_summary(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = current_user.id
    total_predictions = (await db.execute(select(func.count(Prediction.id)).where(Prediction.user_id == uid))).scalar() or 0
    settled_rows = await _settled_predictions_for_user(db, uid)
    wins, settled, streak = _wins_settled_streak(settled_rows)
    accuracy = round(wins / settled, 4) if settled > 0 else 0.0
    xp = (total_predictions * 10 + wins * 20)
    try:
        if hasattr(current_user, "current_streak") and (current_user.current_streak or 0) != streak:
            current_user.current_streak = streak
            await db.commit()
    except Exception:
        await db.rollback()
    u_pred_sub = select(Prediction.id).where(Prediction.user_id == uid).subquery()
    roi_result = (await db.execute(select(func.avg(CLVEntry.profit)).where(CLVEntry.prediction_id.in_(select(u_pred_sub.c.id))))).scalar() or Decimal("0")
    roi_result = roi_result * 100
    user_profit = (await db.execute(select(func.sum(CLVEntry.profit)).where(CLVEntry.prediction_id.in_(select(u_pred_sub.c.id))))).scalar() or Decimal("0")
    active = (await db.execute(select(func.count(Match.id)).where(Match.actual_outcome.is_(None)))).scalar() or 0
    vitcoin_balance = 0.0
    try:
        from app.modules.wallet.models import Wallet
        wallet = (await db.execute(select(Wallet).where(Wallet.user_id == uid))).scalar_one_or_none()
        if wallet:
            vitcoin_balance = float(wallet.vitcoin_balance)
    except Exception:
        pass
    return {
        "total_predictions": total_predictions,
        "accuracy_rate": accuracy,
        "settled_predictions": settled,
        "wins": wins,
        "roi": float(roi_result),
        "active_matches": active,
        "wallet_balance": vitcoin_balance,
        "streak": streak,
        "xp": xp,
        "user_profit": float(user_profit),
    }


@router.get("/vitcoin-price")
async def get_dashboard_vitcoin_price(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    if _price_cache["timestamp"] and (now - _price_cache["timestamp"]).total_seconds() < 300:
        return _price_cache["data"]
    try:
        from app.modules.wallet.pricing import VITCoinPricingEngine
        from app.modules.wallet.models import VITCoinPriceHistory, Wallet, WalletTransaction
        source = "oracle"
        engine = VITCoinPricingEngine(db)
        prices = await engine.get_current_price()
        current = float(prices.get("usd", Decimal("0")))
        if current <= 0:
            source = "synthetic"
            total_vitcoin = (await db.execute(select(func.sum(Wallet.vitcoin_balance)))).scalar() or Decimal("0")
            total_usd_deposited = (await db.execute(
                select(func.sum(WalletTransaction.amount))
                .where(WalletTransaction.currency == 'USD', WalletTransaction.type == 'deposit', WalletTransaction.status == 'confirmed')
            )).scalar() or Decimal("0")
            if total_usd_deposited > 0:
                current = float(total_vitcoin / total_usd_deposited)
            else:
                current = 0.001
                source = "default"
        change_24h = 0.0
        try:
            hist_q = await db.execute(select(VITCoinPriceHistory).order_by(VITCoinPriceHistory.calculated_at.desc()).limit(2))
            history = hist_q.scalars().all()
            if len(history) >= 2:
                prev = float(history[1].price_usd)
                if prev > 0:
                    change_24h = round((current - prev) / prev * 100, 4)
        except Exception:
            pass
        data = {"price": current, "price_usd": current, "change_24h": change_24h, "source": source, "calculated_at": now.isoformat()}
        _price_cache["data"] = data
        _price_cache["timestamp"] = now
        return data
    except Exception as e:
        logger.error(f"Price oracle error: {e}")
        return {"price": 0.001, "price_usd": 0.001, "source": "default", "change_24h": 0.0, "calculated_at": now.isoformat()}


@router.get("/recent-activity")
async def get_recent_activity(limit: int = 10, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    uid = current_user.id
    result = await db.execute(
        select(Match, Prediction).join(Prediction, Match.id == Prediction.match_id)
        .where(Prediction.user_id == uid).order_by(Prediction.timestamp.desc()).limit(limit)
    )
    rows = result.all()
    activity = []
    for match, pred in rows:
        activity.append({
            "id": str(pred.id), "type": "prediction", "description": f"{match.home_team} vs {match.away_team}",
            "bet_side": pred.bet_side, "outcome": match.actual_outcome, "edge": pred.vig_free_edge,
            "created_at": pred.timestamp.isoformat() if pred.timestamp else None,
        })
    return activity

@router.get("/top-opportunities")
async def get_top_opportunities(limit: int = Query(default=5, ge=1, le=20), db: AsyncSession = Depends(get_db)):
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        lookback = now - timedelta(hours=6)
        result = await db.execute(
            select(Match, Prediction).join(Prediction, Match.id == Prediction.match_id)
            .where(Match.actual_outcome.is_(None), Match.kickoff_time >= lookback, Prediction.vig_free_edge.isnot(None))
            .order_by(desc(Prediction.vig_free_edge)).limit(limit)
        )
        rows = result.all()
        opportunities = []
        for match, pred in rows:
            edge_pct = round(float(pred.vig_free_edge or 0) * 100, 1)
            ai_conf = round(float(pred.confidence or 0.75) * 100, 0)
            opportunities.append({
                "match": f"{match.home_team} vs {match.away_team}", "league": match.league or "Unknown",
                "edge": f"+{edge_pct}%" if edge_pct >= 0 else f"{edge_pct}%", "edge_value": edge_pct,
                "ai_confidence": int(ai_conf), "time": str(match.kickoff_time),
                "bet_side": pred.bet_side, "prediction_id": str(pred.id), "match_id": str(match.id),
            })
        return {"opportunities": opportunities, "total": len(opportunities)}
    except Exception as e:
        logger.warning(f"top-opportunities error: {e}")
        return {"opportunities": [], "total": 0}

@router.get("/model-confidence")
async def get_model_confidence(db: AsyncSession = Depends(get_db)):
    try:
        from app.modules.ai.models import ModelMetadata
        result = await db.execute(select(ModelMetadata).order_by(ModelMetadata.accuracy.desc()))
        models = result.scalars().all()
        if models:
            model_list = []
            for m in models:
                model_list.append({
                    "name": m.name or m.key, "key": m.key, "accuracy": round(float(m.accuracy or 0) * 100, 1),
                    "weight": round(float(m.weight or 1.0), 3), "predictions": m.predictions_total or 0,
                    "status": "active" if m.is_active else "inactive",
                })
            total_weight = sum(m["weight"] for m in model_list if m["status"] == "active")
            ensemble_accuracy = sum(m["accuracy"] * m["weight"] for m in model_list if m["status"] == "active") / total_weight if total_weight > 0 else 0.0
            return {"models": model_list, "ensemble_accuracy": round(ensemble_accuracy, 1), "active_count": sum(1 for m in model_list if m["status"] == "active")}
    except Exception as e:
        logger.debug(f"model-confidence registry fallback: {e}")
    return {"models": [], "ensemble_accuracy": 0.0, "active_count": 0}

@router.get("/leaderboard")
async def get_leaderboard(limit: int = Query(default=10, ge=1, le=50), db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).where(User.is_active == True, User.is_banned == False))
        users = result.scalars().all()
        leaderboard = []
        for u in users:
            settled_rows = await _settled_predictions_for_user(db, u.id)
            user_wins, total_settled, streak = _wins_settled_streak(settled_rows)
            total_preds = (await db.execute(select(func.count(Prediction.id)).where(Prediction.user_id == u.id))).scalar() or 0
            xp = u.total_xp if u.total_xp else (total_preds * 10 + user_wins * 20)
            win_rate = round(user_wins / total_settled, 4) if total_settled > 0 else 0.0
            leaderboard.append({
                "username": u.username, "xp": xp, "win_rate": win_rate, "level": "Novice",
                "predictions": total_preds, "streak": streak, "user_profit": 0.0,
            })
        leaderboard.sort(key=lambda x: x["xp"], reverse=True)
        leaderboard = leaderboard[:limit]
        for i, entry in enumerate(leaderboard): entry["rank"] = i + 1
        return {"leaderboard": leaderboard, "total": len(leaderboard)}
    except Exception as e:
        logger.warning(f"leaderboard error: {e}")
        return {"leaderboard": [], "total": 0}

@router.get("/achievements")
async def get_achievements(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        uid = current_user.id
        total_all_preds = (await db.execute(select(func.count(Prediction.id)).where(Prediction.user_id == uid))).scalar() or 0
        settled_rows = await _settled_predictions_for_user(db, uid)
        total_wins, total_settled, _ = _wins_settled_streak(settled_rows)
        win_rate = total_wins / total_settled if total_settled > 0 else 0.0
        vitcoin_balance = 0.0
        try:
            from app.modules.wallet.models import Wallet
            wallet = (await db.execute(select(Wallet).where(Wallet.user_id == uid))).scalar_one_or_none()
            if wallet: vitcoin_balance = float(wallet.vitcoin_balance)
        except Exception: pass
        streak = getattr(current_user, "current_streak", 0) or 0
        achievements = [
            {"id": "first", "name": "First Blood", "earned": total_all_preds >= 1},
            {"id": "accuracy70", "name": "Sharpshooter", "earned": total_settled >= 10 and win_rate >= 0.70},
            {"id": "streak5", "name": "On Fire", "earned": streak >= 5},
            {"id": "prediction50", "name": "Volume Player", "earned": total_all_preds >= 50},
            {"id": "vitcoin1k", "name": "VIT Whale", "earned": vitcoin_balance >= 1000},
        ]
        return {"achievements": achievements}
    except Exception as e:
        logger.warning(f"achievements error: {e}")
        return {"achievements": []}
