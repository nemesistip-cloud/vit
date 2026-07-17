# Audit Report: VIT AI Platform Integration

## 1. What Exists
- **Database Models (`app/modules/ai/models.py`)**: Defines `ModelMetadata` (the model registry table), `AIPredictionAudit` (for detailed audit logs), and `AIInsight` (for persistent match-related insights).
- **In-Memory Orchestrator (`services/ml_service/models/model_orchestrator.py`)**: Implements a 13-model ensemble. In development mode, it acts as a skeleton; in production (or when overridden via env), it loads real trained weights from joblib-serialized `.pkl` files (locally or from Tachyon VESS storage).
- **Registry Synchronization (`app/modules/ai/registry.py`)**: Implements `bootstrap_registry()` to initialize DB rows with canonical metadata.
- **Backend Routes (`app/modules/ai/routes.py`)**: Exposes endpoints under `/api/ai-engine/` for listing models, uploading/promoting pkl versions, triggering weight adjustments, and retrieving audit logs.
- **Frontend Status & Details (`frontend/src/pages/AI.tsx` & `Status.tsx`)**: Renders status summaries of `vit-ai`, but with severe display bugs.

## 2. What's Broken
- **Frontend Model parsing bug**: In `AI.tsx`, the code expects `modelsData.models` (as an object containing an array), but the actual API `/api/v1/models` from the microservice returns a flat JSON array `[ { "id": "lstm_v1", ... }, ... ]`. This mismatch crashes/breaks model list rendering ("No models returned by vit-ai — check the service logs").
- **Static / Stale Health Fields**: The status of `vit-ai` providers and inferencing capabilities are simulated or not properly updated in real-time.
- **Local Dev vs. Prod discrepancy**: In development mode, conftest/database imports for pytest were broken due to circular imports when the `app` module bound itself during startup initialization.

## 3. What's Missing & Gaps
- **Centralized Outbound Client (`vit_ai_client.py`)**: No single service handles calls to the `vit-ai` microservice with proper connection pooling, timeout, retries, circuit breaker, caching, and background health probes.
- **Centralized AI Gateway**: No generic routing gateway to switch between routing modes (cheapest, fastest, accuracy, ensemble, manual, or direct model routing).
- **Interactive Playground**: No UI exists for developers or analysts to test prompts, inspect streaming outputs, change temperatures, see token estimates, or export completions.
- **Production Chat Interface**: Chat UI with history search, Markdown streaming, prompt adjustments, and export functionality is missing.
- **Institutional AI Copilot**: The helper robot `ai_assistant.py` relies on simplistic string keywords rather than dedicated copilot tool structures (e.g. explaining smart contracts, blockchain txs, platform configs).
- **Monitoring & Metrics Dashboards**: Missing metrics visualizer for inference count, errors, provider latencies, and cache-hit ratio.
- **AI Admin Center Panel**: Missing operator switches to enable/disable models, clear cache, adjust routing weights, and manage API keys dynamically.

## 4. Technical Debt & Safety Issues
- Hardcoded defaults in model predictors and fallback pathways.
- Low test coverage for the interactive components of AI orchestration and routing.
- Circular imports during FastAPI lazy loading startup (specifically when `app` is imported inside routes during early initialization).
- Lack of Redis caching on expensive natural language inferences.

## 5. Actionable Recommendations
1. Fix circular import in main.py by avoiding `import app` on sub-routes. (Done!)
2. Patch frontend `AI.tsx` to handle flat arrays.
3. Build the dedicated AI client, routing gateway, and advanced model registry metadata.
4. Implement interactive Chat UI, Developer Playground, Admin Center, and live monitoring dashboards in the Frontend.
5. Securely wrap all mutations with proper JWT verification and input sanitization.
6. Write extensive backend integration tests.
