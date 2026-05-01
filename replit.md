# VIT Sports Intelligence Network

## Overview
The VIT Sports Intelligence Network is an institutional-grade football prediction platform. It leverages a 12-model AI ensemble for predictions, integrates a VITCoin wallet economy, supports blockchain-verified staking, features a model marketplace, and includes a governance DAO. The platform offers multi-tier subscriptions (Free, Pro, Elite) and aims to provide advanced sports analytics and prediction capabilities.

## User Preferences
I prefer iterative development with a focus on clear, modular code. Please use functional programming paradigms where appropriate and provide detailed explanations for significant architectural decisions or complex algorithms. Ask before making major changes to the project structure or core functionalities.

## System Architecture
The platform is built with a microservices-oriented approach.
- **Backend**: Python 3.11 with FastAPI, utilizing SQLAlchemy for asynchronous ORM operations and Alembic for database migrations. Uvicorn serves the application on port 5000.
- **Database**: SQLite is used for development, with PostgreSQL as the production database, configured via `VIT_DATABASE_URL`.
- **Frontend**: Developed using React 18, TypeScript, Vite, TailwindCSS, and ShadCN UI. The build output is located in `frontend/dist/` and served by the FastAPI application.
- **AI Orchestrator**: Manages a 12-model AI ensemble that uses trained `.pkl` weights and per-model calibrators.
- **Authentication**: Implements JWT and TOTP for secure authentication, enforcing 2FA.
- **Wallet & Blockchain**: Includes a VITCoin wallet system and supports blockchain-based staking, though the blockchain features can be optionally disabled.
- **Marketplace**: Features a UI for a model marketplace.
- **Developer API**: Provides key management for external integrations.
- **Notifications**: Uses WebSockets for real-time notifications with exponential reconnect logic.
- **UI/UX**: Frontend components are built with ShadCN UI, utilizing TailwindCSS for styling, ensuring a modern and responsive design.
- **AI Model Calibration**: Employs isotonic calibration for per-model probability adjustments, using fitted calibrators from historical data.
- **Model Weight Adjustment**: A CLV-blended weight adjuster is used for AI models, combining log-loss and Closing Line Value (CLV) signals to dynamically update model contributions.
- **AI Assistant**: A conversational AI assistant is integrated into match-detail pages, providing context-aware answers based on pre-loaded prediction data.
- **Module Map**:
    - AI Orchestrator: Running with trained models and calibrators.
    - Auth (JWT + TOTP): Complete with 2FA.
    - Wallet + VITCoin: Core functionality complete.
    - Predictions: Working.
    - Blockchain / Staking: Disabled by flag.
    - Cross-Chain Bridge: Simulation only.
    - Governance DAO: Partial implementation.
    - Marketplace: UI live.
    - Developer API: Key management done.
    - Notifications + WS: WS toasts + exponential reconnect.
    - Referral: No reward distribution.
    - Trust Engine: Partial.
    - Training Pipeline: Colab-only.

## External Dependencies
- **Football Data API**: Used for fetching football match data.
- **Gemini API**: Integrated for the conversational AI Assistant.
- **Stripe**: Used for subscription management and payments (webhook activated).
- **Paystack**: Enabled for NGN deposits.
- **SMTP Host**: Required for email functionalities (currently stubbed to console).
- **Redis**: Planned for advanced rate limiting (currently in-memory).
- **Anthropic API**: Planned for Claude insights (currently disabled).