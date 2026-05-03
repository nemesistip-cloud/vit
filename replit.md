# VIT Sports Intelligence Network

## Overview
The VIT Sports Intelligence Network is an institutional-grade football prediction platform that employs a 12-model AI ensemble for predictions. It integrates a VITCoin wallet economy, supports blockchain-verified staking, features a model marketplace, and includes a governance DAO. The platform offers multi-tier subscriptions and provides advanced sports analytics, real-time live match tracking, and AI agent intelligence reports. Its business vision is to deliver sophisticated, reliable sports predictions and foster a decentralized, community-driven ecosystem around sports intelligence.

## User Preferences
I prefer iterative development with a focus on clear, modular code. Please use functional programming paradigms where appropriate and provide detailed explanations for significant architectural decisions or complex algorithms. Ask before making major changes to the project structure or core functionalities.

## System Architecture
The platform is built with a microservices-oriented approach.

**Backend:**
- **Core Technology:** Python 3.11 with FastAPI and SQLAlchemy for asynchronous ORM.
- **Database:** SQLite (development), PostgreSQL (production).
- **AI Orchestrator:** Manages a 12-model AI ensemble with dynamic weight adjustment.
- **Multi-Provider AI Client:** Features a cascade fallback system (Gemini → Claude → OpenAI → xAI) with rate-limit awareness.
- **Authentication:** JWT and TOTP for secure 2FA authentication.
- **Prediction System:** Dynamically determines best bet sides and consensus probabilities across various markets.
- **Settlement Pipeline:** Processes match results, updates profit, and attributes CLV.
- **Notification System:** Multi-channel email, Telegram DMs, and in-app WebSockets.
- **Autonomous Agent System:** Comprises 22 agents inheriting from `BaseAgent`, each with a `node_id` and responsible for specific tasks (e.g., `live-match-tracker`, `match-scout`, `news-sentinel`, `oracle-node`, `network-guardian`). Agents record network contributions.
- **VIT Oracle:** A blockchain consensus layer that aggregates match results from agent nodes.
- **VIT DID (Decentralized Identity):** W3C-compliant DID documents for users and agents, with Verifiable Credentials issued by the network.
- **VIT Network Node System:** Tracks `NodeActivity` for agents and aggregates hourly `NetworkSnapshot` data.
- **VIT SCIE (Self-Contained Intelligence Engine):** A zero-external-API dependency layer providing functionalities like `synthetic_odds`, `get_team_form`, `get_head_to_head`, and template fallbacks for agents.
- **ML Accountability System:** Tracks performance metrics for 24 models (12 base + 12 v2) with mechanisms for bootstrapping and reactivating models.
- **Quant Module:** Provides endpoints for financial analysis including `summary`, `backtest`, `monte-carlo` simulations, `ev-scanner`, and `strategy-optimizer`.

**Frontend:**
- **Core Technology:** React 19, TypeScript, Vite, TailwindCSS 4, ShadCN UI.
- **State Management:** `@tanstack/react-query` for server state, `vitWS` singleton for WebSocket.
- **Key Pages:** Includes dashboards for matches, AI agent reports, agent monitoring, match details with AI insights, AI source management, oracle health, and network statistics.
- **Puter AI Integration:** Browser-side AI via Puter.js.

## External Dependencies
- **Football-Data.org:** Live and finished match data.
- **Transfermarkt:** Injury data (scraped).
- **Resend.com / SMTP:** Email notifications.
- **Telegram Bot API:** User DMs and webhooks.
- **Gemini API:** Primary AI provider.
- **Anthropic API (Claude):** Fallback AI provider.
- **OpenAI API:** Fallback AI provider.
- **xAI (Grok):** Fallback AI provider.
- **Puter.js:** Browser-side AI.
- **Stripe:** Subscription checkout.
- **Paystack:** NGN deposits.