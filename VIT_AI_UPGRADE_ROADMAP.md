# VIT AI Upgrade Roadmap (v6.0.0)

This roadmap outlines the plan for upgrading VIT AI into an institutional-grade, secure, hyper-performing service.

## Phase 1: Foundation & Resiliency
- Fix frontend parsing bugs on model arrays.
- Create the centralized, resilient `vit_ai_client.py` with retries, timeout, circuit breaker, and caching.
- Write backend test suites to verify connection resiliency.

## Phase 2: Centralized AI Gateway
- Implement `AIGateway` with routing modes (Fastest, Cheapest, Highest Accuracy, Ensemble, Manual).
- Upgrade the Model Registry in `routes.py` with capabilities, pricing, and token limits.
- Establish secure JWT protection on administrative endpoints.

## Phase 3: Interactive Features
- Build the Developer Playground for testing prompts, temperatures, and system rules.
- Build the Chat Interface with history search, Markdown formatting, and JSON export.
- Implement the AI Copilot to explain blockchain data, smart contracts, and transactions.

## Phase 4: Observability & Management
- Integrate the AI Admin Panel for hot registry, cache flushing, and key rotation.
- Design the Monitoring Dashboards for latency, error rate, and cache hit ratios.
- Run complete automated test pipelines to ensure flawless operation.
