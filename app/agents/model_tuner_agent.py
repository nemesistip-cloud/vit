# app/agents/model_tuner_agent.py
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.db.models import Prediction, ModelPerformance

logger = logging.getLogger(__name__)

class ModelTunerAgent(BaseAgent):
    """
    Agent responsible for analyzing model performance and suggesting
    parameter/weight adjustments using DeepSeek.
    """

    def __init__(self):
        super().__init__(
            name="model-tuner",
            interval_seconds=24 * 60 * 60,
            initial_delay_seconds=300
        )

    async def run_cycle(self) -> Dict[str, Any]:
        """Runs the tuning analysis cycle."""
        # This agent runs once every 24 hours
        last_run = self.state.get("last_run_at")
        if last_run:
            last_run_dt = datetime.fromisoformat(last_run)
            if datetime.now() - last_run_dt < timedelta(hours=24):
                return {"status": "skipped", "reason": "Cooldown (24h)"}

        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            perf_data = await self._fetch_performance_metrics(db)
            if not perf_data:
                return {"status": "skipped", "reason": "No performance data available"}

            suggestions = await self._get_tuning_suggestions(perf_data)

            self.state["last_run_at"] = datetime.now().isoformat()
            self.state["last_suggestions"] = suggestions

            return {
                "status": "complete",
                "suggestions_count": len(suggestions.get("adjustments", [])),
                "primary_recommendation": suggestions.get("summary")
            }

    async def _fetch_performance_metrics(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Fetches recent performance metrics for all models."""
        # Fetch last 30 days of performance
        stmt = select(ModelPerformance).where(
            ModelPerformance.timestamp > datetime.now() - timedelta(days=30)
        ).order_by(ModelPerformance.timestamp.desc())

        result = await db.execute(stmt)
        rows = result.scalars().all()

        return [
            {
                "model_name": r.model_name,
                "accuracy": r.accuracy,
                "brier_score": r.brier_score,
                "roi": r.roi,
                "sample_size": r.sample_size,
                "timestamp": r.timestamp.isoformat()
            } for r in rows
        ]

    async def _get_tuning_suggestions(self, perf_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Asks DeepSeek to analyze performance and suggest adjustments."""
        prompt = f"""
        Analyze the following model performance data for my sports prediction ensemble:
        {json.dumps(perf_data, indent=2)}

        Identify:
        1. Which models are over-performing and should have their weights increased?
        2. Which models are under-performing (high Brier score, negative ROI)?
        3. Specific weight adjustment suggestions (0.0 to 2.0 scale).

        Return a JSON object with:
        "summary": "High-level overview",
        "adjustments": [{{"model": "name", "action": "increase/decrease", "new_weight": 1.2, "reason": "..."}}]
        """

        try:
            from app.services.ai_client import call_ai
            response = await call_ai(
                prompt=prompt,
                temperature=0.2
            )
            # Try to parse JSON from response
            try:
                # Basic cleanup in case LLM adds markdown blocks
                clean_json = response.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()

                return json.loads(clean_json)
            except (json.JSONDecodeError, IndexError, Exception) as parse_err:
                logger.warning(f"Failed to parse AI tuning response as JSON: {parse_err}")
                return {"summary": response, "adjustments": []}
        except Exception as e:
            logger.error(f"Failed to get tuning suggestions: {e}")
            return {"summary": "Error calling AI service", "adjustments": []}
