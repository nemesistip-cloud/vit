# VIT Network API Reference

The VIT Network provides a RESTful API for sports analytics, wallet management, and blockchain interaction.

## Base URL
`https://api.vitnetwork.app/api`

## Authentication
Most endpoints require an API Key. Include it in the header of your requests:
`X-API-Key: your_api_key_here`

---

## 1. Predictions

### Get Consensus Prediction
`GET /predictions/{match_id}`
Returns the ensemble AI and validator consensus for a specific match.

### Stake on Prediction
`POST /predictions/{match_id}/stake`
Place a VIT stake on a specific outcome.

---

## 2. Wallet

### Get Balance
`GET /wallet/balance`
Returns the custodial VIT balance for the authenticated user.

### Transfer VIT (Custodial)
`POST /wallet/transfer`
Transfer VIT to another user within the platform.

### List Transactions
`GET /wallet/transactions`
Get the transaction history for the user.

---

## 3. Tachyon Storage (VESS)

### Upload File
`POST /tachyon/upload`
Multipart upload to the decentralized storage swarm.

### Download File
`GET /tachyon/download/{file_id}`
Retrieve a file by its ID.

---

## 4. Blockchain (VIT Chain)

### JSON-RPC Endpoint
`POST /chain/rpc`
Standard Ethereum-compatible JSON-RPC 2.0 interface.

### Network Economy
`GET /blockchain/economy`
Returns global tokenomics stats (circulating supply, total staked, etc.).

---

## 5. System

### Health Check
`GET /health`
Returns the health status of all internal subsystems.

### Ticker
`GET /ticker`
Live platform stats for the ecosystem ticker.
