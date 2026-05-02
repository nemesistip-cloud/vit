# VIT Sports Intelligence Network

## Overview
The VIT Sports Intelligence Network is an institutional-grade football prediction platform. It utilizes a 12-model AI ensemble for predictions, integrates a VITCoin wallet economy, supports blockchain-verified staking, features a model marketplace, and includes a governance DAO. The platform offers multi-tier subscriptions (Free, Pro, Elite) and aims to provide advanced sports analytics and prediction capabilities, leveraging real historical match data for training and improved weight calculation methods.

## User Preferences
I prefer iterative development with a focus on clear, modular code. Please use functional programming paradigms where appropriate and provide detailed explanations for significant architectural decisions or complex algorithms. Ask before making major changes to the project structure or core functionalities.

## System Architecture
The platform is built with a microservices-oriented approach.

**Backend:**
- **Core Technology:** Python 3.11 with FastAPI, SQLAlchemy for asynchronous ORM, and Alembic for database migrations.
- **Server:** Uvicorn serves the application on port 5000.
- **Database:** PostgreSQL for production, SQLite for development.
- **AI Orchestrator:** Manages a 12-model AI ensemble, loading trained `.pkl` weights and per-model calibrators. It incorporates a CLV-blended weight adjuster for dynamic model contribution updates.
- **Authentication:** JWT and TOTP for secure authentication, including 2FA with DB-backed token revocation and brute-force protection.
- **Prediction System:** Dynamically determines best bet sides, consensus probabilities, and model probabilities for various markets.
- **Settlement Pipeline:** Processes match results, updates prediction outcomes (`was_correct`, `settled_profit`), and handles CLV attribution.
- **Notification System:** Multi-channel notification dispatch supporting email (HTML templates), Telegram DMs (per-user), and in-app WebSockets.
- **Referral System:** Credits referrers with VITCoin on confirmed deposits or subscriptions.
- **KYC CloudChain:** Admin-controlled identity verification with document data collection and approval/rejection workflows.
- **Error Handling:** Backend endpoint for logging frontend client-side errors.

**Frontend:**
- **Core Technology:** React 18, TypeScript, Vite, TailwindCSS, and ShadCN UI.
- **Build Output:** Located in `frontend/dist/` and served by the FastAPI application.
- **UI/UX:** Utilizes ShadCN UI for a modern, responsive design with clear error states and accessibility features (ARIA labels, error banners).
- **Navigation:** Comprehensive sidebar and mobile bottom navigation across key application areas (Bet, Earn, Pro, Network, You).
- **Components:** Includes a shared `EmptyState` component for various no-data scenarios.
- **Performance:** Implements `@tanstack/react-virtual` for list virtualization where applicable.
- **Notifications UI:** User interface for managing notification preferences, including Telegram linking (deep-link and manual entry) and testing.
- **Analytics:** Displays ROI, CLV, and per-model performance charts.
- **Admin Panel:** Features for ML Calibration, Manual Settlement, Global Accumulator, Audit Log, Fixture Ecosystem Health, and CSV uploads.
- **Predictions Page:** Enhanced "Results vs Predictions" view with WIN/LOSS/PENDING badges and detailed comparison ledger.
- **AI Assistant:** Conversational AI assistant integrated into match-detail pages for context-aware answers.

**Testing:**
- **Unit/Integration Tests:** Utilizes Vitest and React Testing Library for comprehensive testing of frontend components and API client logic.

## External Dependencies
- **Football-Data.co.uk:** Source for historical match data.
- **Resend.com:** Preferred API for email notifications.
- **SMTP:** Fallback protocol for email notifications.
- **Telegram Bot API:** For sending per-user direct messages and handling webhook interactions.
- **Gemini API:** Integrated for the conversational AI Assistant.
- **Stripe:** Used for subscription checkout and webhook processing.
- **Paystack:** Used for NGN deposits.
- **Redis:** Planned for advanced rate limiting.
- **Anthropic API:** Planned for Claude insights.