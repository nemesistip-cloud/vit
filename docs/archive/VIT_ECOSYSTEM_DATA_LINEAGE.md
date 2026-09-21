# VIT Ecosystem Data Lineage

## Sports intelligence

```text
External sports providers / historical CSV and JSON
  -> provider/client and ingestion modules (PARTIAL)
  -> validation/normalization (PARTIAL, not fully runtime-proven)
  -> sports models and Alembic tables (PRESENT)
  -> feature/model services (PARTIAL)
  -> prediction/ensemble gateway (PARTIAL)
  -> API/page consumers (PRESENT, contract/runtime not proven)
  -> Matches / MatchDetail / Predictions UI (PRESENT)
```

**Integrity finding:** `data/historical_matches.csv`, `.json`, and training artifacts demonstrate available historical/seed material, not live freshness. Source attribution, timestamps, provider failure behavior, prediction persistence, and outcome evaluation must be verified before labeling outputs live.

## AI request lineage

```text
Frontend/API caller
  -> AIGateway.route_chat
  -> detect_intent
  -> vit_ai_client.call_ai (external path)
  -> local orchestrator fallback
  -> fixed offline fallback string if both fail
  -> wrapped response with provider/model/status/latency
```

The wrapper is real, but a returned response can be fallback text. Consumers must use `provider`, `model_id`, `status`, and `is_fallback`; response text alone is not proof of model inference.

## Chain lineage

```text
Client/RPC caller
  -> vit_chain RPC router/handlers
  -> transaction/block core
  -> crypto verification
  -> state/consensus components
  -> chain storage/indexer
  -> query/explorer consumers
```

Core modules and tests exist. The missing evidence is the running path across network reception, validation, quorum/finality, persistence, restart recovery, and explorer/API consumption.

## Node/storage lineage

```text
CLI setup
  -> encrypted keystore + JSON NodeConfig
  -> Google Drive OAuth token
  -> NodeIdentity registration
  -> VITNodeDaemon
  -> P2P handshake (public key derived from encrypted keystore; server-side signature verification remains absent)
  -> storage monitor + earnings sync + receive loop
```

The path is structurally connected, but external OAuth, registration, authenticated P2P, reward settlement, and restart behavior are not verified.

## Exchange lineage

```text
Exchange order input
  -> exchange models/order book
  -> matching engine
  -> executor
  -> wallet balances/settlement
  -> persistence/API/frontend
```

Order book and matching code exist, but the complete durable settlement path is not evidenced. Treat exchange UI claims as prototype/partial until authenticated, concurrent, persistent integration passes.

## Commerce lineage

```text
Marketplace UI/routes
  -> marketplace service/models/merchant
  -> catalog/vendor/order/payment components
  -> webhook/notification paths
  -> wallet/chain settlement (unverified)
```

No verified executable Piluno integration or complete VIT payment-to-chain path was established.

## Data quality controls required

- record provider and retrieval timestamps
- distinguish live, historical, seeded, mocked, and fallback records in API schemas
- persist model version and feature snapshot with predictions
- preserve raw provider payloads where allowed for auditability
- add lineage and freshness assertions to integration tests
- prevent fallback responses from being presented as successful inference
