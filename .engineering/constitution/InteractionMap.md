# Master Interaction Map

## 1. User Lifecycle

### Workflow: User Registration (Social Auth)
- **Initiator**: User (Frontend) via Google/Telegram OAuth.
- **Participating Modules**: `Identity`, `Wallet`, `Database`, `Infrastructure`.
- **Data Flow**: Social Profile -> User Model -> Wallet Creation -> Welcome Bonus Injection.
- **Events Emitted**: `user.login.google` or `user.login.telegram` (Audit Log).
- **Failure Handling**: 401 on invalid token, 403 on banned user, 500 on DB failure (rolls back user creation).
- **Completion State**: JWT Tokens (Access/Refresh) returned to frontend.

### Workflow: Identity Verification (KYC)
- **Initiator**: User (Frontend) uploading documents.
- **Participating Modules**: `Identity`, `Storage (Tachyon)`, `Admin`.
- **Data Flow**: Image Upload -> Tachyon Sharding -> KYC Model Record -> Admin Review.
- **Completion State**: User status updated to `is_verified=True`.

## 2. Prediction Lifecycle

### Workflow: Market Analysis & Prediction
- **Initiator**: User or Automated Agent.
- **Participating Modules**: `Core (Sports)`, `AI (Intelligence)`, `Database`, `Task System`, `Notifications (Telegram)`.
- **Data Flow**: Fixture ID -> AI Orchestrator -> Multi-Model Inference -> Ensemble Result -> Bankroll Check -> Prediction Save.
- **Events Emitted**: `prediction_created`, `bet_alert_sent` (Telegram).
- **Failure Handling**: AI timeouts fall back to deterministic insights or vig-free removal logic.
- **Completion State**: Prediction record saved with `vig_free_edge` and `confidence`.

### Workflow: Match Settlement (Oracle-based)
- **Initiator**: Background Task (Celery) or External Webhook.
- **Participating Modules**: `Blockchain (Consensus)`, `Core (Sports)`, `Wallet`, `Database`.
- **Data Flow**: Final Score -> Oracle Results -> Consensus Bridge -> 67% Threshold Check -> Market Settlement.
- **Events Emitted**: `market_settled`, `payout_distributed`.
- **Failure Handling**: Insufficient consensus triggers admin review or oracle retry.
- **Completion State**: `ConsensusPrediction` status updated to `SETTLED`.

## 3. Financial Workflows

### Workflow: Wallet Deposit (Fiat Gateway)
- **Initiator**: User (Frontend) via Paystack/Flutterwave.
- **Participating Modules**: `Wallet`, `Infrastructure`, `External (Payment API)`.
- **Data Flow**: Checkout Session -> User Payment -> Webhook Notification -> Balance Update.
- **Events Emitted**: `deposit_confirmed`, `transaction_logged`.
- **Failure Handling**: Signature verification prevents spoofing; failed transactions remain in `pending` or `failed` status.
- **Completion State**: `vitcoin_balance` incremented in `Wallet`.

### Workflow: P2P Trading (Escrow)
- **Initiator**: Buyer/Seller.
- **Participating Modules**: `Wallet`, `Blockchain (Escrow)`, `Database`.
- **Data Flow**: Order Creation -> VITCoin Lock in Escrow -> Payment Proof -> Escrow Release.
- **Completion State**: VITCoin transferred from Seller to Buyer wallet.

## 4. AI & Data Workflows

### Workflow: Model Training & Deployment
- **Initiator**: Admin or Automated Schedule.
- **Participating Modules**: `AI (Inference)`, `Task System`, `Storage (Cloud Storage)`.
- **Data Flow**: Historical Fixtures -> Feature Engineering -> XGBoost/LSTM Training -> Model Weight Save -> Registry Reload.
- **Completion State**: New model version active in the Ensemble.

## 5. Marketplace & Rewards

### Workflow: Marketplace Purchase
- **Initiator**: User (Frontend).
- **Participating Modules**: `Marketplace`, `Wallet`, `Database`.
- **Data Flow**: Item Selection -> Balance Check -> VITCoin Debit -> Item Unlock/Issuance.
- **Completion State**: User has access to the purchased asset; Wallet balance updated.

### Workflow: Validator Reward Distribution
- **Initiator**: `Blockchain` (Consensus Settlement).
- **Participating Modules**: `Wallet`, `Blockchain`, `Notification`.
- **Data Flow**: Settlement Confirmation -> Reward Calculation -> Wallet Credit -> In-App Notification.
- **Completion State**: Validator balance incremented.

### Workflow: Governance Voting
- **Initiator**: User (Voter).
- **Participating Modules**: `Governance`, `Blockchain`, `Database`.
- **Data Flow**: Proposal Selection -> Signature Verification -> Vote Record -> Tally Update.
- **Completion State**: Vote recorded on-chain or in the high-fidelity ledger.
