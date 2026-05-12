# app/services/model_accountability.py
import logging
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.db.models import ModelPerformance, Prediction

logger = logging.getLogger(__name__)

# Unified weight bounds — must match weight_adjuster.py constants
_MIN_WEIGHT = 0.10
_MAX_WEIGHT = 5.00


class ModelAccountability:
    """Enforce model accountability with automatic weight decay."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_model_weights(self):
        """Update model weights based on recent settled prediction performance.

        Uses Prediction.was_correct directly so the update loop fires even when
        CLV entries are absent (previously the inner join to clv_entries returned
        0 rows, causing every model to be silently skipped every cycle).
        """
        result = await self.db.execute(select(ModelPerformance))
        models = result.scalars().all()

        from app.modules.ai.models import ModelMetadata
        for model in models:
            recent_predictions = await self._get_recent_performance(model.model_name)

            if len(recent_predictions) < model.performance_window:
                continue

            accuracy = float(sum(p["is_correct"] for p in recent_predictions)) / len(recent_predictions)
            clv_vals = [p["clv"] for p in recent_predictions if p["clv"] is not None]
            clv = float(sum(clv_vals) / len(clv_vals)) if clv_vals else 0.0

            if accuracy < 0.5 or clv < -0.02:
                model.current_weight *= (1 - model.weight_decay_rate)
                model.consecutive_underperforming += 1
                logger.warning(
                    "Model %s underperforming (acc=%.3f clv=%.4f) — weight decayed to %.4f",
                    model.model_name, accuracy, clv, model.current_weight,
                )
            else:
                model.consecutive_underperforming = 0
                model.current_weight = min(_MAX_WEIGHT, model.current_weight * 1.02)

            # Enforce unified floor/ceiling
            model.current_weight = max(_MIN_WEIGHT, min(_MAX_WEIGHT, model.current_weight))
            # Also honour the per-row threshold (may be higher than the global floor)
            model.current_weight = max(model.current_weight, model.min_weight_threshold)
            model.last_weight_update = datetime.now(timezone.utc)
            model.accuracy_score = accuracy

            # Sync weight to ModelMetadata so both systems share one source of truth
            try:
                meta_row = await self.db.execute(
                    select(ModelMetadata).where(ModelMetadata.key == model.model_name)
                )
                meta = meta_row.scalar_one_or_none()
                if meta:
                    meta.weight = model.current_weight
            except Exception as _e:
                logger.debug("ModelMetadata sync skipped for %s: %s", model.model_name, _e)

        await self.db.commit()

    async def _get_recent_performance(self, model_name: str, days: int = 30) -> List[Dict]:
        """Get recent performance metrics for a model.

        Queries Prediction directly (no CLV join) so the loop works even when
        clv_entries is empty.  CLV is populated when available from CLVEntry;
        otherwise clv=None (handled upstream as neutral signal).
        """
        from app.db.models import CLVEntry
        from sqlalchemy.orm import aliased

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Fetch settled predictions; LEFT-join CLVEntry so rows still come back
        # even when the closing price was never recorded.
        clv_alias = aliased(CLVEntry)
        stmt = (
            select(Prediction, clv_alias)
            .outerjoin(clv_alias, Prediction.id == clv_alias.prediction_id)
            .where(
                Prediction.timestamp >= cutoff_date,
                Prediction.was_correct.isnot(None),  # only settled rows
            )
            .order_by(Prediction.timestamp.desc())
            .limit(200)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        recent: List[Dict] = []
        for pred, clv_row in rows:
            recent.append({
                "is_correct": bool(pred.was_correct),
                "clv": float(clv_row.clv) if clv_row and clv_row.clv is not None else None,
                "edge": pred.vig_free_edge,
            })
        return recent

    async def get_model_report(self) -> Dict:
        """Get accountability report for all models."""
        result = await self.db.execute(select(ModelPerformance))
        models = result.scalars().all()

        return {
            "models": [
                {
                    "name": m.model_name,
                    "current_weight": m.current_weight,
                    "accuracy": m.accuracy_score,
                    "consecutive_underperforming": m.consecutive_underperforming,
                    "needs_review": m.consecutive_underperforming > 5,
                }
                for m in models
            ],
            "total_weight": sum(m.current_weight for m in models),
        }
