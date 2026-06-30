# Ecosystem Architecture Diagram (Textual)

## 1. System Overview

```text
[ Users (Web/Mobile) ] <--- HTTPS (TLS 1.3) ---> [ GCP Load Balancer ]
                                                        |
                                                        V
                                              [ Cloud Run (API Gateway) ]
                                                        |
      +-----------------+-------------------------------+-------------------+-----------------+
      |                 |                               |                   |                 |
      V                 V                               V                   V                 V
[ Identity ]      [ AI Module ]                  [ Sports Module ]    [ Wallet Module ] [ Blockchain ]
(OAuth/KYC)       (Inference)                    (Fixtures/Odds)      (Balance/P2P)     (L2 Settlement)
      |                 |                               |                   |                 |
      +-----------------+-------------------------------+-------------------+-----------------+
                                                        |
                                                        V
                                     +-----------------------------------------+
                                     |           Core Persistence              |
                                     |   [ PostgreSQL ]      [ Memorystore ]   |
                                     |   (Data Truth)        (Cache/Tasks)     |
                                     +-----------------------------------------+
                                                        |
                                                        V
                                     +-----------------------------------------+
                                     |           Storage & Ledger              |
                                     |   [ Tachyon VESS ]    [ Base Mainnet ]  |
                                     |   (Sharded Data)      (L2 Ledger)       |
                                     +-----------------------------------------+
```

## 2. Component Relationships

### Frontend <-> Core API
- **Protocol**: RESTful HTTP / WebSockets.
- **Data Flow**: High-density JSON terminals.

### Core API <-> Persistence
- **PostgreSQL**: ORM (SQLAlchemy) via AsyncPG.
- **Memorystore**: Redis pub/sub and distributed locking.

### AI <-> External
- **Sports Providers**: iSports, Football-Data.org.
- **Intelligence**: Native ensemble inference.

### Wallet <-> Financial
- **Fiat**: Paystack, Flutterwave (Webhooks).
- **Crypto**: Base L2 (RPC).

## 3. Runtime Lifecycle

- **Startup**:
  1. Load Secrets.
  2. Init DB Connection.
  3. Load AI Model Registry.
  4. Start Ticker/Sync loops.
- **Shutdown**:
  1. Graceful drain of active HTTP requests.
  2. Flush Redis buffers.
  3. Close DB pool.
