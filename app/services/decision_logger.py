# app/services/decision_logger.py
import json
import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DecisionLog

logger = logging.getLogger(__name__)


class DecisionLogger:
    """Log every betting decision with full context"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_decision(
        self,
        match_id: int,
        prediction_id: int,
        decision: Dict[str, Any],
        context: Dict[str, Any]
    ):
        """Log a betting decision"""
        log_entry = DecisionLog(
            match_id=match_id,
            prediction_id=prediction_id,
            decision_type=decision.get("type", "bet"),
            stake=decision.get("stake"),
            odds=decision.get("odds"),
            edge=decision.get("edge"),
            reason=decision.get("reason"),
            model_contributions=json.dumps(decision.get("model_weights", {})),
            market_context=json.dumps(context.get("market", {})),
            bankroll_state=json.dumps(context.get("bankroll", {})),
            timestamp=datetime.utcnow()
        )
        self.db.add(log_entry)
        await self.db.commit()

        logger.info(f"Decision logged: match={match_id}, stake={decision.get('stake')}, reason={decision.get('reason')}")

    async def get_decision_history(self, limit: int = 100) -> list:
        """Get recent decision history"""
        from sqlalchemy import select

        result = await self.db.execute(
            select(DecisionLog)
            .order_by(DecisionLog.timestamp.desc())
            .limit(limit)
        )

        logs = result.scalars().all()
        return [
            {
                "match_id": log.match_id,
                "stake": log.stake,
                "odds": log.odds,
                "edge": log.edge,
                "reason": log.reason,
                "timestamp": log.timestamp.isoformat()
            }
            for log in logs
        ]