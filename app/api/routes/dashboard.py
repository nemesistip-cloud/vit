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


@router.get("/summary")
async def get_dashboard_summary(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = current_user.id

    total_predictions = (
        await db.execute(
            select(func.count(Prediction.id)).where(Prediction.user_id == uid)
        )
    ).scalar() or 0

    u_pred_sub = select(Prediction.id).where(Prediction.user_id == uid).subquery()

    settled = (
        await db.execute(
            select(func.count(CLVEntry.id))
            .where(CLVEntry.prediction_id.in_(select(u_pred_sub.c.id)))
            .where(CLVEntry.bet_outcome.in_(["win", "loss"]))
        )
    ).scalar() or 0

    wins = (
        await db.execute(
            select(func.count(CLVEntry.id))
            .where(CLVEntry.prediction_id.in_(select(u_pred_sub.c.id)))
            .where(CLVEntry.bet_outcome == "win")
        )
    ).scalar() or 0

    accuracy = round(wins / settled, 4) if settled > 0 else 0.0

    roi_result = (
        await db.execute(
            select(func.sum(CLVEntry.profit))
            .where(CLVEntry.prediction_id.in_(select(u_pred_sub.c.id)))
        )
    ).scalar() or Decimal("0")

    active = (
        await db.execute(
            select(func.count(Match.id)).where(Match.actual_outcome.is_(None))
        )
    ).scalar() or 0

    vitcoin_balance = 0.0
    try:
        from app.modules.wallet.models import Wallet
        wallet = (
            await db.execute(select(Wallet).where(Wallet.user_id == uid))
        ).scalar_one_or_none()
        if wallet:
            vitcoin_balance = float(wallet.vitcoin_balance)
    except Exception:
        pass

    streak = getattr(current_user, "current_streak", 0) or 0

    return {
        "total_predictions": total_predictions,
        "accuracy_rate": accuracy,
        "roi": float(roi_result),
        "active_matches": active,
        "wallet_balance": vitcoin_balance,
        "streak": streak,
    }


@router.get("/vitcoin-price")
async def get_dashboard_vitcoin_price(db: AsyncSession = Depends(get_db)):
    try:
        from app.modules.wallet.pricing import VITCoinPricingEngine
        from app.modules.wallet.models import VITCoinPriceHistory
        engine = VITCoinPricingEngine(db)
        prices = await engine.get_current_price()
        current = float(prices.get("usd", Decimal("0.001")))

        change_24h = 0.0
        try:
            hist_q = await db.execute(
                select(VITCoinPriceHistory)
                .order_by(VITCoinPriceHistory.calculated_at.desc())
                .limit(2)
            )
            history = hist_q.scalars().all()
            if len(history) >= 2:
                prev = float(history[1].price_usd)
                if prev > 0:
                    change_24h = round((current - prev) / prev * 100, 4)
        except Exception:
            pass

        return {"price": current, "change_24h": change_24h}
    except Exception:
        return {"price": 0.001, "change_24h": 0.0}


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = 10,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = current_user.id
    result = await db.execute(
        select(Match, Prediction)
        .join(Prediction, Match.id == Prediction.match_id)
        .where(Prediction.user_id == uid)
        .order_by(Prediction.timestamp.desc())
        .limit(limit)
    )
    rows = result.all()
    activity = []
    for match, pred in rows:
        activity.append({
            "id": str(pred.id),
            "type": "prediction",
            "description": f"{match.home_team} vs {match.away_team}",
            "bet_side": pred.bet_side,
            "outcome": match.actual_outcome,
            "edge": pred.vig_free_edge,
            "created_at": pred.timestamp.isoformat() if pred.timestamp else None,
        })
    return activity


@router.get("/top-opportunities")
async def get_top_opportunities(
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        lookback = now - timedelta(hours=6)

        result = await db.execute(
            select(Match, Prediction)
            .join(Prediction, Match.id == Prediction.match_id)
            .where(Match.actual_outcome.is_(None))
            .where(Match.kickoff_time >= lookback)
            .where(Prediction.vig_free_edge.isnot(None))
            .order_by(desc(Prediction.vig_free_edge))
            .limit(limit)
        )
        rows = result.all()

        opportunities = []
        for match, pred in rows:
            edge_pct = round(float(pred.vig_free_edge or 0) * 100, 1)
            ai_conf = round(float(pred.confidence or 0.75) * 100, 0)
            kickoff = match.kickoff_time
            if isinstance(kickoff, datetime):
                if kickoff.date() == now.date():
                    time_label = f"Today {kickoff.strftime('%H:%M')}"
                elif kickoff.date() == (now + timedelta(days=1)).date():
                    time_label = f"Tomorrow {kickoff.strftime('%H:%M')}"
                else:
                    time_label = kickoff.strftime("%b %d %H:%M")
            else:
                time_label = str(kickoff)

            opportunities.append({
                "match": f"{match.home_team} vs {match.away_team}",
                "league": match.league or "Unknown",
                "edge": f"+{edge_pct}%" if edge_pct >= 0 else f"{edge_pct}%",
                "edge_value": edge_pct,
                "ai_confidence": int(ai_conf),
                "time": time_label,
                "bet_side": pred.bet_side,
                "prediction_id": str(pred.id),
                "match_id": str(match.id),
            })

        return {"opportunities": opportunities, "total": len(opportunities)}
    except Exception as e:
        logger.warning(f"top-opportunities error: {e}")
        return {"opportunities": [], "total": 0}


@router.get("/model-confidence")
async def get_model_confidence(db: AsyncSession = Depends(get_db)):
    try:
        from app.modules.ai.models import ModelMetadata
        result = await db.execute(
            select(ModelMetadata).order_by(ModelMetadata.accuracy_score.desc())
        )
        models = result.scalars().all()

        if models:
            model_list = []
            for m in models:
                model_list.append({
                    "name": m.model_name or m.model_key,
                    "key": m.model_key,
                    "accuracy": round(float(m.accuracy_score or 0) * 100, 1),
                    "weight": round(float(m.current_weight or 1.0), 3),
                    "predictions": m.total_predictions or 0,
                    "status": "active" if m.is_active else "inactive",
                })

            total_weight = sum(m["weight"] for m in model_list if m["status"] == "active")
            ensemble_accuracy = (
                sum(m["accuracy"] * m["weight"] for m in model_list if m["status"] == "active")
                / total_weight if total_weight > 0 else 0.0
            )

            return {
                "models": model_list,
                "ensemble_accuracy": round(ensemble_accuracy, 1),
                "active_count": sum(1 for m in model_list if m["status"] == "active"),
            }
    except Exception as e:
        logger.debug(f"model-confidence registry fallback: {e}")

    try:
        from app.modules.ai.models import AIPredictionAudit
        result = await db.execute(
            select(AIPredictionAudit).order_by(AIPredictionAudit.created_at.desc()).limit(1)
        )
        audit = result.scalar_one_or_none()
        if audit and audit.model_outputs:
            models_data = []
            for key, val in audit.model_outputs.items():
                if isinstance(val, dict):
                    conf = val.get("confidence", 0.75)
                    models_data.append({
                        "name": key.replace("_v1", "").replace("_", " ").title(),
                        "key": key,
                        "accuracy": round(float(conf) * 100, 1),
                        "weight": 1.0,
                        "predictions": 0,
                        "status": "active",
                    })
            if models_data:
                avg_acc = sum(m["accuracy"] for m in models_data) / len(models_data)
                return {"models": models_data, "ensemble_accuracy": round(avg_acc, 1), "active_count": len(models_data)}
    except Exception as e:
        logger.debug(f"model-confidence audit fallback: {e}")

    return {"models": [], "ensemble_accuracy": 0.0, "active_count": 0}


@router.get("/leaderboard")
async def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Return top users ranked by prediction performance (XP = predictions*10 + wins*20)."""
    try:
        result = await db.execute(
            select(User).where(User.is_active == True, User.is_banned == False)
        )
        users = result.scalars().all()

        leaderboard = []
        for u in users:
            u_pred_sub = select(Prediction.id).where(Prediction.user_id == u.id).subquery()

            total_settled = (await db.execute(
                select(func.count(CLVEntry.id))
                .where(CLVEntry.prediction_id.in_(select(u_pred_sub.c.id)))
                .where(CLVEntry.bet_outcome.in_(["win", "loss"]))
            )).scalar() or 0

            user_wins = (await db.execute(
                select(func.count(CLVEntry.id))
                .where(CLVEntry.prediction_id.in_(select(u_pred_sub.c.id)))
                .where(CLVEntry.bet_outcome == "win")
            )).scalar() or 0

            total_preds = (await db.execute(
                select(func.count(Prediction.id)).where(Prediction.user_id == u.id)
            )).scalar() or 0

            stored_xp = getattr(u, "total_xp", None) or 0
            xp = stored_xp if stored_xp > 0 else (total_preds * 10 + user_wins * 20)
            win_rate = round(user_wins / total_settled, 4) if total_settled > 0 else 0.0
            streak = getattr(u, "current_streak", 0) or 0

            tier = u.subscription_tier or "viewer"
            level_map = {"viewer": "Novice", "analyst": "Analyst", "pro": "Pro", "elite": "Elite"}
            level = level_map.get(tier, "Novice")

            leaderboard.append({
                "username": u.username,
                "xp": xp,
                "win_rate": win_rate,
                "level": level,
                "predictions": total_preds,
                "streak": streak,
            })

        leaderboard.sort(key=lambda x: x["xp"], reverse=True)
        leaderboard = leaderboard[:limit]
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1

        return {"leaderboard": leaderboard, "total": len(leaderboard)}
    except Exception as e:
        logger.warning(f"leaderboard error: {e}")
        return {"leaderboard": [], "total": 0}


@router.get("/achievements")
async def get_achievements(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return achievement status for the current user based on real per-user activity."""
    try:
        uid = current_user.id
        u_pred_sub = select(Prediction.id).where(Prediction.user_id == uid).subquery()

        total_settled = (await db.execute(
            select(func.count(CLVEntry.id))
            .where(CLVEntry.prediction_id.in_(select(u_pred_sub.c.id)))
            .where(CLVEntry.bet_outcome.in_(["win", "loss"]))
        )).scalar() or 0

        total_all_preds = (await db.execute(
            select(func.count(Prediction.id)).where(Prediction.user_id == uid)
        )).scalar() or 0

        total_wins = (await db.execute(
            select(func.count(CLVEntry.id))
            .where(CLVEntry.prediction_id.in_(select(u_pred_sub.c.id)))
            .where(CLVEntry.bet_outcome == "win")
        )).scalar() or 0

        win_rate = total_wins / total_settled if total_settled > 0 else 0.0

        vitcoin_balance = 0.0
        try:
            from app.modules.wallet.models import Wallet
            wallet = (await db.execute(
                select(Wallet).where(Wallet.user_id == uid)
            )).scalar_one_or_none()
            if wallet:
                vitcoin_balance = float(wallet.vitcoin_balance)
        except Exception:
            pass

        is_validator = current_user.role == "validator"
        streak = getattr(current_user, "current_streak", 0) or 0

        achievements = [
            {"id": "first", "name": "First Blood", "description": "Make your first prediction",
             "icon": "🎯", "earned": total_all_preds >= 1, "rarity": "common"},
            {"id": "accuracy70", "name": "Sharpshooter", "description": "Reach 70% win rate (min 10 settled)",
             "icon": "🎖️", "earned": total_settled >= 10 and win_rate >= 0.70, "rarity": "rare"},
            {"id": "streak5", "name": "On Fire", "description": "Win 5 predictions in a row",
             "icon": "🔥", "earned": streak >= 5, "rarity": "rare"},
            {"id": "prediction50", "name": "Volume Player", "description": "Make 50 predictions",
             "icon": "📊", "earned": total_all_preds >= 50, "rarity": "common"},
            {"id": "vitcoin1k", "name": "VIT Whale", "description": "Accumulate 1,000 VITCoin",
             "icon": "🐋", "earned": vitcoin_balance >= 1000, "rarity": "epic"},
            {"id": "validator", "name": "Network Defender", "description": "Become a validator",
             "icon": "🛡️", "earned": is_validator, "rarity": "legendary"},
        ]
        return {"achievements": achievements}
    except Exception as e:
        logger.warning(f"achievements error: {e}")
        return {"achievements": []}
