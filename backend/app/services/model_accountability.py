# app/services/model_accountability.py
import logging
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta, timezone
import numpy as np

from app.db.models import ModelPerformance, Prediction, CLVEntry

logger = logging.getLogger(__name__)


class ModelAccountability:
    """Enforce model accountability with automatic weight decay"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def seed_from_registry(self) -> int:
        """Ensure every active ModelMetadata row has a matching ModelPerformance row.

        Called at startup (and lazily from update_model_weights) so the weight
        optimizer always has rows to work with, even on a fresh deployment where
        no predictions have been settled yet.

        Returns the number of newly created rows (0 if all already present).
        """
        from app.modules.ai.models import ModelMetadata
        from app.modules.ai.registry import MODEL_SPECS

        result = await self.db.execute(
            select(ModelMetadata).where(ModelMetadata.is_active == True)
        )
        meta_rows = result.scalars().all()

        # Build set of already-tracked model names
        existing = await self.db.execute(select(ModelPerformance.model_name))
        existing_names = {row[0] for row in existing.fetchall()}

        inserted = 0
        for meta in meta_rows:
            if meta.key in existing_names:
                continue
            # Use spec weight as the initial current_weight so
            # the model starts at its design-spec contribution.
            spec_weight = MODEL_SPECS.get(meta.key, {}).get("spec_weight", 0.08)
            perf = ModelPerformance(
                model_name=meta.key,
                model_type=meta.model_type or "unknown",
                current_weight=spec_weight,
                min_weight_threshold=max(spec_weight * 0.25, 0.01),
                weight_decay_rate=0.05,
                performance_window=50,  # lower than default 100 so tracking kicks in sooner
            )
            self.db.add(perf)
            inserted += 1
            logger.info("[accountability] seeded ModelPerformance row for %s (weight=%.4f)", meta.key, spec_weight)

        if inserted:
            await self.db.commit()
            logger.info("[accountability] seeded %d ModelPerformance rows from registry", inserted)
        return inserted

    async def update_model_weights(self):
        """Update model weights based on recent performance.

        Auto-seeds ModelPerformance rows from the registry first so this
        method always has rows to work with on fresh deployments.
        """
        # Auto-seed missing rows before querying (idempotent — safe to call every cycle)
        await self.seed_from_registry()

        # Get all models
        result = await self.db.execute(select(ModelPerformance))
        models = result.scalars().all()

        from app.modules.ai.models import ModelMetadata
        for model in models:
            # Get recent performance
            recent_predictions = await self._get_recent_performance(model.model_name)

            if len(recent_predictions) < model.performance_window:
                continue

            # Calculate performance metrics
            accuracy = float(np.mean([p['is_correct'] for p in recent_predictions]))
            clv_vals = [p['clv'] for p in recent_predictions if p['clv'] is not None]
            clv = float(np.mean(clv_vals)) if clv_vals else 0.0

            # Apply weight decay if underperforming
            if accuracy < 0.5 or clv < -0.02:
                model.current_weight *= (1 - model.weight_decay_rate)
                model.consecutive_underperforming += 1
                logger.warning(f"Model {model.model_name} weight decayed to {model.current_weight:.3f}")
            else:
                model.consecutive_underperforming = 0
                # Slight boost for good performance
                model.current_weight = min(1.0, model.current_weight * 1.02)

            # Enforce minimum weight
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
                logger.debug(f"ModelMetadata sync skipped for {model.model_name}: {_e}")

        await self.db.commit()

    async def _get_recent_performance(self, model_name: str, days: int = 30) -> List[Dict]:
        """Get recent performance metrics for a model"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(Prediction, CLVEntry)
            .join(CLVEntry, Prediction.id == CLVEntry.prediction_id)
            .where(Prediction.timestamp >= cutoff_date)
            .order_by(Prediction.timestamp.desc())
            .limit(200)
        )

        predictions = result.all()
        recent = []
        for pred, clv in predictions:
            # Determine if prediction was correct
            probs = {"home": pred.home_prob, "draw": pred.draw_prob, "away": pred.away_prob}
            predicted = max(probs, key=probs.get)
            is_correct = (predicted == pred.bet_side) if pred.bet_side else False

            recent.append({
                'is_correct': is_correct,
                'clv': clv.clv if clv else None,
                'edge': pred.vig_free_edge
            })

        return recent

    async def get_model_report(self) -> Dict:
        """Get accountability report for all models"""
        result = await self.db.execute(select(ModelPerformance))
        models = result.scalars().all()

        return {
            "models": [
                {
                    "name": m.model_name,
                    "current_weight": m.current_weight,
                    "accuracy": m.accuracy_score,
                    "consecutive_underperforming": m.consecutive_underperforming,
                    "needs_review": m.consecutive_underperforming > 5
                }
                for m in models
            ],
            "total_weight": sum(m.current_weight for m in models)
        }
