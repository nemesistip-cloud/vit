# VIT AI Platform: API Specification (v6.0.0)

This document provides the canonical API endpoints, request schemas, and response formats for the upgraded **VIT AI Gateway and Model Registry**.

---

## 🔒 Authentication
All mutating endpoints require authentication.
- **Third-Party / Gateway Integration**: Authenticate via `X-API-Key` headers.
- **Admin Endpoints**: Enforce standard bearer-token JWT authorization.

---

## 1. Model Registry Endpoints

### 1.1 List All Models
- **Endpoint**: `GET /api/ai-engine/models`
- **Response Format**:
```json
{
  "models": [
    {
      "id": 1,
      "key": "xgb_v2",
      "name": "XGBoost",
      "model_type": "XGBoost",
      "version": "v4.6.0",
      "weight": 1.2,
      "accuracy": 0.781,
      "is_active": true,
      "token_limit": 4096,
      "pricing_metadata": {
        "input_1k_tokens": 0.0,
        "output_1k_tokens": 0.0
      },
      "fallback_priority": 2,
      "endpoint": "https://vit-ai.onrender.com/api/v1/models/xgb_v2",
      "capabilities": ["prediction", "inference"],
      "default": true
    }
  ]
}
```

### 1.2 Hot-Register Model
- **Endpoint**: `POST /api/ai-engine/models/register`
- **Request Body**:
```json
{
  "key": "custom_lstm_v1",
  "name": "Custom LSTM Pattern",
  "model_type": "LSTM",
  "description": "Tailored sequence-aware prediction model.",
  "supported_markets": ["1x2", "over_under"]
}
```
- **Response**: `201 Created`

---

## 2. Interactive AI Chat & Copilot

### 2.1 Chat / Query Assist
- **Endpoint**: `POST /ai/assistant/chat`
- **Request Body**:
```json
{
  "message": "Audit on-chain transaction hash 0x7a2c4e...",
  "history": []
}
```
- **Response**:
```json
{
  "available": true,
  "reply": "### VIT Financial Rails & Ledger\n- **Details**: Resolved Keccak-256 DID signature...",
  "thoughts": ["Auditing Payment Rails and Wallet balances"]
}
```

---

## 3. Administrative Control Endpoints

### 3.1 Adjust Weights
- **Endpoint**: `PATCH /api/ai-engine/models/{key}/weight`
- **Request Body**: `{"weight": 1.5}`

### 3.2 Clear Cache
- **Endpoint**: `POST /api/ai-engine/weights/sync`
- **Summary**: Synchronizes DB weights with the in-memory orchestrator and invalidates stale Redis query caches.
