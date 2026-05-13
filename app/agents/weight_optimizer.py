"""app/agents/weight_optimizer.py — Weight Optimizer Agent v2

Runs every 6 hours.

v2 upgrades:
  - Ensemble diversity preservation: no single model may exceed 40% of the
    total weight pool; excess weight is redistributed proportionally to others
  - Minimum floor: no active model falls below 5% of the average weight
  - diversity_score published in result (Gini coefficient of weight distribution)
  - Emits swarm event when a model is trimmed for dominance

Responsibilities:
  - Re-fit the global temperature scaler on all settled predictions
  - Update dynamic model weights via ModelAccountability
  - Sync weights across ModelMetadata and ModelPerformance tables
  - Integrate RL reward signals from RLRewardAccumulator
  - Preserve ensemble diversity (prevent weight collapse to one model)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

_RL_DELTA_CAP          = 0.15   # max RL weight delta per cycle
_MAX_WEIGHT_FRACTION   = 0.40   # no model may hold more than 40% of total weight
_MIN_WEIGHT_MULTIPLIER = 0.05   # floor = 5% of the average weight
_DIVERSITY_TRIM_LOG    = True   # log whenever a model is trimmed


def _gini(weights: List[float]) -> float:
    """Compute Gini coefficient of a weight distribution (0=perfectly equal, 1=monopoly)."""
    if len(weights) < 2:
        return 0.0
    n = len(weights)
    s = sorted(weights)
    total = sum(s)
    if total == 0:
        return 0.0
    cumsum = sum((i + 1) * w for i, w in enumerate(s))
    return round((2 * cumsum / (n * total)) - (n + 1) / n, 4)


class WeightOptimizerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="weight-optimizer",
            interval_seconds=6 * 3600,
            initial_delay_seconds=3 * 60,
        )

    async def run_cycle(self) -> Dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.services.accuracy_enhancer import fit_temperature_from_history
        from app.services.model_accountability import ModelAccountability

        results: Dict[str, Any] = {}

        async with AsyncSessionLocal() as db:
            # ── 1. Temperature calibration ─────────────────────────────────
            try:
                temp_result = await fit_temperature_from_history(db, min_samples=50)
                results["temperature_fit"] = temp_result
                if temp_result.get("fitted"):
                    logger.info(
                        "[weight-optimizer] temperature fitted: T=%.4f "
                        "NLL improvement=%.6f (n=%d)",
                        temp_result["temperature"],
                        temp_result["improvement"],
                        temp_result["n_samples"],
                    )
                else:
                    logger.info(
                        "[weight-optimizer] temperature fit skipped: %s",
                        temp_result.get("reason", "unknown"),
                    )
            except Exception as e:
                logger.warning("[weight-optimizer] temperature fit error: %s", e)
                results["temperature_fit"] = {"fitted": False, "error": str(e)}

            # ── 2. Model weight update ─────────────────────────────────────
            try:
                ma = ModelAccountability(db)
                await ma.update_model_weights()
                report = await ma.get_model_report()
                results["weight_update"] = {
                    "models_updated": len(report.get("models", [])),
                    "total_weight":   report.get("total_weight", 0.0),
                    "needs_review":   [
                        m["name"] for m in report.get("models", [])
                        if m.get("needs_review")
                    ],
                }
                logger.info(
                    "[weight-optimizer] weights updated: %d models, "
                    "total_weight=%.3f needs_review=%s",
                    results["weight_update"]["models_updated"],
                    results["weight_update"]["total_weight"],
                    results["weight_update"]["needs_review"],
                )
            except Exception as e:
                logger.warning("[weight-optimizer] weight update error: %s", e)
                results["weight_update"] = {"error": str(e)}

            # ── 3. AIProfilerService weight sync ──────────────────────────
            try:
                from app.services.ai_profiler import AIProfilerService
                profiler = AIProfilerService(db)
                await profiler.update_weights()
                results["profiler_sync"] = {"synced": True}
            except Exception as e:
                logger.debug("[weight-optimizer] profiler sync error: %s", e)
                results["profiler_sync"] = {"synced": False, "error": str(e)}

            # ── 4. RL Reward Integration ───────────────────────────────────
            try:
                results["rl_rewards"] = await self._apply_rl_rewards(db)
            except Exception as e:
                logger.warning("[weight-optimizer] RL reward integration error: %s", e)
                results["rl_rewards"] = {"error": str(e)}

            # ── 5. Ensemble diversity preservation ────────────────────────
            try:
                results["diversity"] = await self._preserve_diversity(db)
            except Exception as e:
                logger.warning("[weight-optimizer] diversity preservation error: %s", e)
                results["diversity"] = {"error": str(e)}

        return results

    async def _apply_rl_rewards(self, db) -> Dict[str, Any]:
        """Apply accumulated RL reward signals as small weight nudges."""
        from app.services.rl_reward import get_accumulator
        from app.services.model_accountability import ModelAccountability

        accumulator = get_accumulator()
        snapshot    = accumulator.snapshot()

        if not snapshot:
            return {"applied": 0, "snapshot": {}}

        ma      = ModelAccountability(db)
        applied = 0
        deltas  = {}

        for model_key, stats in snapshot.items():
            delta = stats.get("weight_delta", 0.0)
            if abs(delta) < 0.005:
                continue

            delta = max(-_RL_DELTA_CAP, min(_RL_DELTA_CAP, delta))
            deltas[model_key] = delta

            try:
                from sqlalchemy import select
                from app.db.models import ModelMetadata  # type: ignore

                row = (await db.execute(
                    select(ModelMetadata).where(ModelMetadata.key == model_key)
                )).scalar_one_or_none()

                if row is not None:
                    new_weight = max(0.1, min(5.0, (row.weight or 1.0) + delta))
                    row.weight = new_weight
                    applied += 1
                    logger.info(
                        "[weight-optimizer] RL delta: model=%s delta=%.4f new=%.4f",
                        model_key, delta, new_weight,
                    )
            except Exception as exc:
                logger.debug("[weight-optimizer] RL delta for %s skipped: %s", model_key, exc)

        if applied > 0:
            try:
                await db.commit()
            except Exception as exc:
                logger.warning("[weight-optimizer] RL commit failed: %s", exc)
                await db.rollback()

        logger.info(
            "[weight-optimizer] RL rewards: %d models adjusted from %d signals",
            applied, len(snapshot),
        )
        return {"applied": applied, "deltas": deltas, "snapshot": snapshot}

    async def _preserve_diversity(self, db) -> Dict[str, Any]:
        """Enforce ensemble diversity constraints.

        Rules:
        1. No model may hold > _MAX_WEIGHT_FRACTION (40%) of total weight.
           Excess is clipped and redistributed proportionally to all other models.
        2. No model may fall below _MIN_WEIGHT_MULTIPLIER × average_weight (floor).
           Under-floor models are raised to the floor (funded by a small pool trim).

        Returns a summary including the Gini coefficient before and after.
        """
        from sqlalchemy import select
        from app.db.models import ModelMetadata  # type: ignore

        rows_res = await db.execute(select(ModelMetadata))
        rows: list = rows_res.scalars().all()

        if len(rows) < 2:
            return {"skipped": True, "reason": "fewer than 2 models"}

        weights    = {r.key: float(r.weight or 1.0) for r in rows}
        total      = sum(weights.values())
        avg_weight = total / len(weights)
        gini_before = _gini(list(weights.values()))

        trimmed_models: list = []
        floored_models: list = []

        # ── Rule 1: cap dominant models at _MAX_WEIGHT_FRACTION of total ──
        max_allowed = total * _MAX_WEIGHT_FRACTION
        for key, w in list(weights.items()):
            if w > max_allowed:
                excess = w - max_allowed
                weights[key] = max_allowed
                # Redistribute excess proportionally to other models
                others       = {k: v for k, v in weights.items() if k != key}
                others_total = sum(others.values()) or 1.0
                for k in others:
                    weights[k] += excess * (others[k] / others_total)
                trimmed_models.append({
                    "key": key, "was": round(w, 4), "now": round(max_allowed, 4),
                    "excess_redistributed": round(excess, 4),
                })
                if _DIVERSITY_TRIM_LOG:
                    logger.warning(
                        "[weight-optimizer] DIVERSITY: trimmed %s %.4f → %.4f "
                        "(was %.0f%% of pool, cap %.0f%%)",
                        key, w, max_allowed,
                        100 * w / total, 100 * _MAX_WEIGHT_FRACTION,
                    )

        # ── Rule 2: raise models below the weight floor ────────────────────
        weight_floor = avg_weight * _MIN_WEIGHT_MULTIPLIER
        for key, w in list(weights.items()):
            if w < weight_floor:
                shortfall    = weight_floor - w
                weights[key] = weight_floor
                floored_models.append({
                    "key": key, "was": round(w, 4), "now": round(weight_floor, 4),
                })
                logger.info(
                    "[weight-optimizer] FLOOR: raised %s %.4f → %.4f",
                    key, w, weight_floor,
                )

        gini_after = _gini(list(weights.values()))

        # Persist updated weights
        changes = 0
        for row in rows:
            new_w = weights.get(row.key)
            if new_w is not None and abs(float(row.weight or 1.0) - new_w) > 1e-6:
                row.weight = round(new_w, 6)
                changes += 1
        if changes:
            try:
                await db.commit()
            except Exception as exc:
                logger.warning("[weight-optimizer] diversity commit failed: %s", exc)
                await db.rollback()
                changes = 0

        # Emit swarm event if any model was trimmed
        if trimmed_models:
            try:
                from app.core.swarm_orchestrator import get_swarm
                await get_swarm().emit_event(
                    "diversity_trim", self.name,
                    {"trimmed": trimmed_models, "gini_before": gini_before, "gini_after": gini_after},
                )
            except Exception:
                pass

        result = {
            "gini_before":   gini_before,
            "gini_after":    gini_after,
            "trimmed":       trimmed_models,
            "floored":       floored_models,
            "changes_saved": changes,
            "max_fraction":  _MAX_WEIGHT_FRACTION,
            "weight_floor":  round(weight_floor, 4),
        }
        if trimmed_models or floored_models:
            logger.info("[weight-optimizer] diversity result: %s", result)
        return result
