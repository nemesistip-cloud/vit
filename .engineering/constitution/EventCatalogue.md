# Master Event Catalogue

## 1. System Events

### Event: `user_registered`
- **Publisher**: `Identity Module` (Social Auth)
- **Consumers**: `Wallet Module` (Welcome Bonus), `Notification Module` (Welcome Message).
- **Payload**: `{ "user_id": 123, "email": "user@example.com", "provider": "google" }`
- **Priority**: High
- **Retry Policy**: 3 attempts via Celery.
- **Idempotency**: `user_id` unique check in Wallet.
- **Security**: Internal.

### Event: `prediction_created`
- **Publisher**: `AI Module` (Inference Engine)
- **Consumers**: `Notification Module` (Telegram Alert), `Task Module` (Gamification logic).
- **Payload**: `{ "prediction_id": 456, "match_id": 789, "edge": 0.05, "confidence": 0.8 }`
- **Priority**: High
- **Idempotency**: `prediction_id` check.
- **Monitoring**: Latency from inference to alert.

### Event: `market_settled`
- **Publisher**: `Blockchain Module` (Consensus Bridge)
- **Consumers**: `Wallet Module` (Payouts), `Task Module` (User Stats update).
- **Payload**: `{ "match_id": 789, "outcome": "home", "payout_total": 500.0 }`
- **Priority**: Critical
- **Retry Policy**: Infinite retry with exponential backoff for payouts.
- **Idempotency**: Transaction-level idempotency using `settlement_id`.
- **Security**: Signed by Validator Network.

## 2. Notification Events (Multi-channel)

| Event Type | Publisher | Consumers | Payload Key Fields | Security |
| :--- | :--- | :--- | :--- | :--- |
| `PREDICTION_ALERT` | AI Service | Web Push, Telegram, In-App | `match`, `confidence` | Public |
| `MATCH_RESULT` | Settlement | Email, Telegram, In-App | `score`, `outcome` | Public |
| `WALLET_ACTIVITY` | Wallet | Email, Push, In-App | `action`, `amount` | Private |
| `VALIDATOR_REWARD`| Blockchain | Email, In-App | `amount`, `match_id` | Private |
| `SYSTEM` | Admin | All Channels | `message` | Public |

## 3. Operational Events

### Event: `tachyon_shard_challenge`
- **Publisher**: `Tachyon Manager`
- **Consumers**: `Storage Nodes`
- **Payload**: `{ "shard_id": "abc-123", "challenge_nonce": "xyz..." }`
- **Monitoring**: Success rate of shard proofs.

### Event: `model_registry_update`
- **Publisher**: `Training Pipeline`
- **Consumers**: `AI Dispatchers`
- **Payload**: `{ "model_name": "XGBoost-Premier", "version": "v1.2.3" }`
- **Idempotency**: Atomic registry swap.
