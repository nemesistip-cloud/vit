# VIT System Upgrade Plan

## Purpose
This document captures the major bug fixes, robustness improvements, and feature upgrades needed to make the VIT Sports Intelligence platform stable, consistent, and production-grade.

## 1. Current risk areas

### Backend
- Inconsistent API error handling: many routes raise `HTTPException(404, "...")` with raw strings.
- Training route state is partially implemented, but frontend and backend have overlapping training flow expectations.
- AI assistant route is coupled to API-key validation only and returns inconsistent status/provider information.
- Startup uses print statements instead of structured logging and lacks module health endpoints.
- Model registry, promotion, and rollback exist but are not fully surfaced or audited.

### AI Assistant
- `Gemini` wrapper is brittle and may fail during tool-calling loops.
- Backend status logic reports provider availability incorrectly.
- Frontend `Puter` integration depends on a global `window.puter` and hard-coded prompts.
- AI analysis prompts demand strict JSON output, which is fragile.

### Frontend
- Hard-coded text strings are pervasive in pages and components.
- `window.location` and raw host building are used in client code, risking incorrect URL resolution.
- Training UI contains placeholder copy and labels that are not fully backed by API behavior.
- 404/empty states are scattered and not centralized.

### Training and models
- `.pkl` model upload and artifact management are only lightly validated.
- No shared schema for uploaded training datasets.
- Training pipeline persistence is mixed between in-memory state and DB.
- Job progress streaming exists, but the UI and backend recovery paths need hardening.

## 2. Upgrade goals

### Stability & correctness
- Standardize API contract and error payloads.
- Enforce auth/security consistently across all endpoints.
- Make training jobs and model promotion durable across restarts.
- Harden AI assistant tool execution and fallback behavior.

### Observability & recovery
- Add health endpoints for AI, training, wallet, blockchain, and marketplace.
- Use structured logging and background task supervision.
- Add progress recovery for training jobs from the database.

### UX & polish
- Remove hard-coded strings and centralize copy.
- Improve 404, error, and empty states.
- Provide clear admin dashboards for AI engine and training.
- Add end-user assistant status and fallback messaging.

### Feature upgrade
- AI assistant orchestration across Gemini, Claude, and Puter.
- Real ML training pipeline with queueing, progress streaming, and model version control.
- Model registry UI with version history, performance audit, promote/rollback.
- Dataset quality scoring with reward/explanation workflow.
- Unified health/diagnostic dashboard for core system modules.

## 3. Implementation phases

### Phase 1: Audit + alignment
1. Map frontend API expectations to backend route implementations.
2. Standardize route prefixes and response models.
3. Create shared error schema and replace raw `HTTPException(..., "...")` patterns.
4. Add a `GET /health` and module-level health endpoints.

### Phase 2: AI assistant hardening
1. Refactor `app/services/gemini_chat.py` to validate Gemini schema and tool-call results.
2. Add provider fallback logic and clearer status reporting.
3. Add admin controls for assistant configuration/tracing.
4. Improve frontend assistant error handling and provider selection.

### Phase 3: Training engine stabilization
1. Harden `/training` job persistence and restore logic.
2. Improve SSE progress streaming and fallback for backend restarts.
3. Add version comparison and promotion UI support.
4. Add dataset schema validation and QA to `app/modules/training/routes.py`.

### Phase 4: UX cleanup
1. Centralize UI copy and component text constants.
2. Replace raw host/url building in frontend utilities.
3. Improve 404/error pages and training dashboard messaging.
4. Add guided admin dashboards for AI and training.

### Phase 5: Testing & observability
1. Add unit tests for backend routes, auth, and error responses.
2. Add frontend tests for assistant chat, training progress, and 404 flows.
3. Add monitoring/alerts for background task failures.
4. Add CI checks for route contract coverage.

## 4. Minimum viable upgrade scope
The first major upgrade should deliver:
- Robust `/training` API with persistent job state, progress SSE, promote/rollback, and version compare.
- Stable AI assistant endpoint with provider health and fallback.
- Shared error handling and consistent backend response shapes.
- Removal of the most dangerous hard-coded UI behaviours.
- Modular health endpoints for core services.

## 5. Next concrete steps
1. Implement shared API error response helpers.
2. Refactor `app/api/routes/ai_assistant.py` status and auth behavior.
3. Harden `app/api/routes/training.py` progress recovery and promotion semantics.
4. Centralize frontend API route definitions and remove raw host construction.
5. Add a validation layer for training dataset uploads.

---

> This plan is the first step toward a high-availability VIT system with robust AI, model management, and a production-ready user experience.
