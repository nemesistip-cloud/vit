# Changelog: VIT AI Platform Integration (v6.0.0)

All notable changes introduced to the VIT AI subsystems are recorded here.

---

## [6.0.0] - July 2026

### Added
- **AI Gateway (`gateway.py`)**: Centralized router class with support for Fastest, Cheapest, Highest Accuracy, Ensemble, and Manual routing modes.
- **Outbound AI Client (`vit_ai_client.py`)**: Built robust HTTP client featuring connection pooling, tenacity retries, circuit-breaker switches, and Redis cache integration.
- **Hot-Registration API (`routes.py`)**: Exposed `POST /api/ai-engine/models/register` to support on-the-fly registration of custom models into the active registry database.
- **Interactive Developer Playground**: Beautiful workspace supporting prompt submission, temperature modifiers, token size sliders, cost estimations, and Markdown outputs.
- **Production Chat & Copilot UI**: Interactive messaging layout supporting multiple sessions, session searches, and pre-coded "Copilot" helper tasks (explain blockchain, smart contracts, transactions, platform troubleshooting).
- **Live Monitoring dashboard**: Progress trackers showing gateway CPU utilization, RAM limits, Virtual GPU load, and live Redis cache ratios.
- **AI Admin Center**: Quick controls to clear Redis cache segments, restart backend model containers, and sliders to adjust model weights.

### Fixed
- **Model Parsing Bug**: Patched `AI.tsx` parsing to elegantly support flat JSON arrays returned by `GET /api/v1/models` instead of crashing the UI or registry lists.
- **Circular Imports**: Fixed circular package bindings on Gunicorn imports by changing nested namespace references.

### Changed
- **Upgraded Model Metadata**: Exposes token limits, pricing specifications, priorities, and capabilities in the default API.
- **Centralized Call Engine**: Integrated `AIGateway` directly with `app/services/ai_client.py` so all platform features inherit the routing engine automatically.
