# Data Ownership Matrix

## 1. Domain Data Ownership

| Entity | Authoritative Owner | Read Models | Write Models | Caching Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **User Profile** | Identity | Identity, Admin | Identity | In-process (Local) |
| **Wallet/Balance** | Wallet | Wallet, Admin | Wallet | Redis (Distributed) |
| **Match/Fixture** | Sports | Sports, AI, Admin | Sports | Redis (60s TTL) |
| **Prediction** | AI | AI, Sports, Users | AI | Redis (Short-lived) |
| **Oracle Result** | Blockchain | Blockchain, Sports | Blockchain | Database Only |
| **Tachyon Shard** | Tachyon | Tachyon, AI | Tachyon | Local Node Cache |
| **Audit Log** | Infrastructure | Admin | All (via Service) | Database Only |

## 2. Persistence & Lifecycle

- **authoritative Store**: PostgreSQL (Cloud SQL) is the source of truth for all relational data.
- **Long-term Storage**:
  - Sharded match data -> Tachyon Swarm.
  - Model weights -> GCP Cloud Storage.
- **Retention**:
  - **Audit Logs**: 1 year.
  - **Historical Matches**: Indefinite (for AI training).
  - **User Sessions**: 7 days (JWT Refresh TTL).

## 3. Data Flow Rules
1. **Owner Writes Only**: Only the domain owner (see `03_BOUNDING_CONTEXTS.md`) is permitted to modify its authoritative tables.
2. **Read via API/Contract**: Other domains MUST read data via formalized contracts or read-only service methods.
3. **Replication**: Cloud SQL automated backups and point-in-time recovery (PITR) enabled.
