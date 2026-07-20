# VIT Network — Security Architecture & Threat Model

**Version:** 6.0.0
**Domain:** /docs/security/
**Status:** Architecture Approved

---

## 1. Overview & Threat Vector Analysis

The VIT Network operates in a highly adversarial global landscape where financial mutations, machine-learning analytics, and private storage assets are potential targets for attackers. This document specifies our comprehensive Security Threat Model, highlighting defensive gates and cryptographic safeguards.

---

## 2. Authentication & JWT Validation Protocol

Session management is powered by **JSON Web Tokens (JWT)**. To prevent token forgery, session hijacking, or replay attacks, the following controls are strictly enforced:

### 2.1 Cryptographic Signature Verification
- **Algorithm:** HS256 (HMAC with SHA-256).
- **Default Hardening:** In production, if `JWT_SECRET_KEY` matches a known development default, the application kernel immediately aborts startup to prevent brute-forcing.
- **Expiration Thresholds:** Access tokens have a maximum TTL of **15 minutes**; refresh tokens have a maximum TTL of **7 days**.

### 2.2 Token Revocation and Rotation (Refresh Token Rotation)
To prevent stolen refresh tokens from maintaining active sessions indefinitely, we implement **Refresh Token Rotation (RTR)**:
- Every time a refresh token is presented at `/api/auth/refresh`, the old token's unique identifier (`jti`) is added to the `token_blocklist` table.
- A new, single-use refresh token is issued.
- If a revoked `jti` is reused, the entire session tree associated with that user ID is immediately invalidated, forcing a full logout across all clients.

---

## 3. Role-Based Access Control (RBAC) Boundaries

Access boundaries are validated by the FastAPI middleware stack. Users are assigned strict administrative and operational roles:

```
                  ┌───────────────────────────────┐
                  │          SUPER ADMIN          │ (Full access to secrets,
                  └──────────────┬────────────────┘  database, and config)
                                 ▼
                  ┌───────────────────────────────┐
                  │             ADMIN             │ (Manage models, seed matches,
                  └──────────────┬────────────────┘  resolve disputes)
                                 ▼
                  ┌───────────────────────────────┐
                  │           VALIDATOR           │ (Sign blocks, submit proofs,
                  └──────────────┬────────────────┘  vote on-chain)
                                 ▼
                  ┌───────────────────────────────┐
                  │             USER              │ (Place stakes, upload storage,
                  └───────────────────────────────┘  query assistant)
```

- **Auditing Constraint:** Every mutating request targeting an admin route (`/api/admin/...`) must compile a structured audit log and append it to the `audit_logs` table before the transaction is committed.

---

## 4. Input Validation & Brute-Force Safeguards

### 4.1 Pydantic Schema Hardening
All REST input vectors are parsed by **Pydantic v2** models to enforce strict type checking and sanitize inputs. String fields must have clear character length boundaries (`min_length`, `max_length`) to protect against buffer overflow or SQL injection payloads.

### 4.2 Database Brute-Force Protection
To defend against automated credential stuffing, VIT implements a double-layered lockout protocol:
1. **In-Memory Rate Limiter:** The `_check_and_record_attempt` sliding window blocks IP ranges with a 429 status if they hit the 10-attempt threshold within 15 minutes.
2. **DB-Backed Lockout (SEC-10):** A user's `failed_login_count` is persisted to the `User` table. If it exceeds 5 consecutive failures, the `locked_until` timestamp is set to 30 minutes in the future, surviving server restarts and worker migrations.

---

## 5. Security Threat Matrix

Below is our categorized threat and mitigation index:

| Threat vector | Severity | Primary Target | Architectural Mitigation |
| :--- | :--- | :--- | :--- |
| **Brute-Force Login** | High | Auth Endpoint | DB-backed lockout (SEC-10) + sliding rate limiter |
| **Token Forgery** | Critical | Gateway Auth | Production fail-fast on default `SECRET_KEY` |
| **SQL Injection** | High | Database / ORM | Exclusively use Async SQLAlchemy ORM parameterized queries |
| **Man-in-the-Middle** | High | Rest Traffic | Set HSTS headers via `SecurityHeadersMiddleware` |
| **Double Spend** | Critical | Wallet Ledger | Unique constraint on `WalletTransaction.reference` + Row-level locking |

This security architecture guarantees that VIT Network maintains an institutional level of **Trust** and **Value** under any network condition.
