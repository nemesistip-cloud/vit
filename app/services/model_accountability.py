# app/services/model_accountability.py
import logging
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
import numpy as np

from app.db.models import ModelPerformance, Prediction, CLVEntry

logger = logging.getLogger(__name__)


class ModelAccountability:
    """Enforce model accountability with automatic weight decay"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def update_model_weights(self):
        """Update model weights based on recent performance"""
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
            model.last_weight_update = datetime.utcnow()
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
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
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