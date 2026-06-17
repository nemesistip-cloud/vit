### Summary of Changes

1. **Prediction Engine Gaps**:
   - Created `app/agents/prediction_agent.py` for background prediction generation.
   - Updated `main.py` to include the `PredictionAgent` in the supervisor.
   - Fixed Celery task mappings in `app/worker/tasks/agents.py`.
   - Updated Celery Beat schedule in `app/worker/beat_schedule.py`.

2. **ML & Hybrid Mode**:
   - Refactored `app/services/multi_sport_orchestrator.py` to support "Hybrid Mode" (ML + SCIE Fallback).
   - Ensured the orchestrator handles non-football sports gracefully.

3. **Tactical Insights**:
   - Enhanced `app/agents/match_scout_agent.py` and `app/services/vit_analytics.py` for richer tactical factors.
   - Upgraded `app/services/deterministic_insights.py` for high-fidelity fallback reasoning.

4. **Stability & Performance**:
   - Updated `scripts/start_production.sh` to enable real ML models and hybrid fallback.
   - Implemented `app/api/routes/model_performance.py` for model accountability.
   - Fixed various technical bugs and ensured async compatibility.
