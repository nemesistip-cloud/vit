# VIT Sports Intelligence Network

## Overview
The VIT Sports Intelligence Network is an institutional-grade football prediction platform utilizing a 12-model AI ensemble. It features a VITCoin wallet economy, blockchain-verified staking, a model marketplace, and a governance DAO. The platform offers multi-tier subscriptions, advanced sports analytics, real-time live match tracking, and AI agent intelligence reports. Its core purpose is to deliver reliable sports predictions and foster a decentralized, community-driven ecosystem for sports intelligence.

## User Preferences
I prefer iterative development with a focus on clear, modular code. Please use functional programming paradigms where appropriate and provide detailed explanations for significant architectural decisions or complex algorithms. Ask before making major changes to the project structure or core functionalities.

## System Architecture
The platform employs a microservices-oriented architecture.

**Backend:**
- **Core Technology:** Python 3.11 with FastAPI and SQLAlchemy (async ORM).
- **Database:** PostgreSQL (production), SQLite (development) with WAL mode.
- **AI Orchestrator:** Manages a 12-model AI ensemble with dynamic weight adjustment.
- **Multi-Provider AI Client:** Cascade fallback (Gemini → Claude → OpenAI → xAI/Grok → Puter) with rate-limit awareness.
- **Authentication:** JWT and TOTP for 2FA.
- **Prediction System:** Dynamically determines best bet sides and consensus probabilities.
- **Settlement Pipeline:** Processes match results and updates profit.
- **Notification System:** Email, Telegram DMs, and in-app WebSockets.
- **Autonomous Agent System:** 22 specialized agents (e.g., `live-match-tracker`, `news-sentinel`) inheriting from `BaseAgent`, recording network contributions.
- **VIT Oracle:** Blockchain consensus layer for aggregating match results from agent nodes.
- **VIT DID:** W3C-compliant Decentralized Identities for users and agents with Verifiable Credentials.
- **VIT Network Node System:** Tracks `NodeActivity` and aggregates `NetworkSnapshot` data.
- **VIT SCIE (Self-Contained Intelligence Engine):** Provides zero-external-API functionalities like `synthetic_odds` and `get_team_form`.
- **ML Accountability System:** Tracks performance for 24 models (12 base + 12 v2).
- **Quant Module:** Provides financial analysis endpoints for `summary`, `backtest`, `monte-carlo` simulations, `ev-scanner`, and `strategy-optimizer`.
- **Smart Contract Engine:** Deterministic rule-based execution engine with built-in handlers for VITToken, Staking, Prediction, Governance, and Treasury contracts.
- **Treasury System:** Manages 8 treasury pools (e.g., validator_rewards, ecosystem_grants) for deposits, allocations, and grant proposals.
- **Merit Protocol:** Tracks `UserMeritScore` with 7 tiers (unranked to sovereign), applying bonus VIT.
- **AI Verification Layer:** Manages `AIModelAttestation` (model registry), `AIOutputAnchor` (prediction hash anchoring), and `AIDisputeRecord`.
- **Security Layer:** Implements `SybilProfile` (composite anomaly scoring), `FraudAlert`, `MultiSigOperation`, and `WalletFreeze`.
- **Sub-Chain Architecture:** Manages 8 specialized sub-chains (e.g., predictions, oracle, governance) for scalability.
- **AI Agent Registry:** Registers and tracks on-chain agents with DIDs, capabilities, stakes, and reputations.
- **Storage Verification:** Manages `StorageContentRecord` (CID, Merkle root, Blake3 hash) and `StorageChallenge` for proof-of-storage.
- **System Identity Module (`app/modules/identity/`):** Issues deterministic `VIT-YYYY-XXXXXX` System IDs per user (SHA-256 derived, no external APIs). Tracks tier (Basic/Standard/Verified/Elite), badge claims, and DID linkage. Endpoints: `GET /api/identity/me`, `POST /api/identity/refresh`, `GET /api/identity/{sid}`, `GET /api/identity/admin/list`.
- **KYC Module (`app/modules/kyc/`):** Fully offline, rule-based identity verification engine. Checks: name plausibility, age (18+), document type, document number patterns per type, nationality. Produces risk score (0–100) and auto-decides approve/manual_review/reject without external API keys. Endpoints: `POST /api/kyc/submit`, `GET /api/kyc/status`, admin queue/approve/reject/audit. `KYCScreenerAgent` processes pending submissions on a 10-minute cycle using the same rule engine.

**Frontend:**
- **Core Technology:** React 19, TypeScript, Vite, TailwindCSS 4, ShadCN UI.
- **State Management:** `@tanstack/react-query` for server state, `vitWS` singleton for WebSocket.
- **Key Pages:** Dashboards for matches, AI agent reports, match details with AI insights, oracle health, network statistics, staking marketplace, blockchain analytics, smart contract browser, treasury management, merit leaderboard, security panels, System Identity card (`/identity`), and KYC Verification form (`/kyc`).
- **Puter AI Integration:** Browser-side AI via Puter.js.

## External Dependencies
- **The Odds API:** For live bookmaker odds and arbitrage opportunities.
- **TheSportsDB:** Primary fixture source (free API).
- **Transfermarkt:** Provides injury data (scraped).
- **Resend.com / SMTP:** Email notifications.
- **Telegram Bot API:** User DMs and webhooks.
- **Gemini API:** Primary AI provider.
- **Anthropic API (Claude):** Fallback AI provider.
- **OpenAI API:** Fallback AI provider.
- **xAI (Grok):** Fallback AI provider.
- **Puter.js:** Browser-side AI (client-side) and server-side Puter (fallback AI provider).
- **Stripe:** Subscription checkout.
- **Paystack:** NGN deposits.