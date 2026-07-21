# VIT Network — Architecture Decision Records (ADRs)

**Version:** 6.0.0
**Domain:** /docs/adr/
**Status:** Approved

---

## ADR 001: Authentication Rate Limiter Migration

### Context
The legacy sliding-window rate-limiting implementation in `app/auth/routes.py` utilized a local, thread-locked dictionary (`_LOGIN_ATTEMPTS`). This design caused three severe vulnerabilities:
1. **Denial of Service Vector:** It recorded every incoming request as a failure before verifying the password, meaning legitimate users could be locked out by third-party spam.
2. **Cluster Multi-Node Invisibility:** Volatile in-memory dictionaries are isolated to individual container instances and are wiped on server redeployment.
3. **No Timing Attack Protection:** Password evaluation was not protected by constant-time validation.

### Decision
Migrate the rate-limiting system from volatile in-memory storage to a **Redis-backed token bucket algorithm**. Attempt counters will only be incremented *after* a password verification failure occurs. Additionally, failed login counts must be persisted to the `User` table (SEC-10) to survive container restarts.

### Consequences
- **Positive:** Wipes out the account-stuffing DoS vector.
- **Positive:** Survives server restarts and scales across multi-container load balancers.
- **Neutral:** Adds a hard dependency on Redis availability during authentication.

---

## ADR 002: Secure Genesis Token Minting Protocol

### Context
A core vulnerability in decentralized platforms is the "Genesis Exploit," where a compromise of the administrator's key allows unlimited token minting.

### Decision
We enforce a rigid **5-phase cryptographic ceremony** for the Genesis Token Minting. The administrator cannot mint tokens single-handedly. Instead, the transaction requires a physical **2-of-3 ECDSA co-signature** using keys derived from distinct hardware/external wallets. Total initial supply is hard-capped at $1,000,000$ VITCoin, with a strict minimum of $70\%$ allocated to the multi-sig treasury.

### Consequences
- **Positive:** Cryptographically guarantees that no single key compromise can inflate the supply.
- **Positive:** Immutably records the mint parameters inside the genesis block.
- **Negative:** Increases manual configuration steps during the node bootstrap wizard.

---

## ADR 003: Tachyon VESS Erasure Coding Specification

### Context
Decentralized storage nodes are inherently transient. To guarantee high availability, files must be shredded and redundant parity blocks must be calculated.

### Decision
Enforce a static Reed-Solomon Erasure Coding configuration of **$K=6$ data shards and $M=3$ parity shards** (K=6, M=3) for all Tachyon VESS uploads. Shards are standard $4\text{ KB}$ fragments distributed across independent cloud backends (Google Drive, Dropbox, OneDrive, Disk).

### Consequences
- **Positive:** Any file can be fully reassembled even if 3 of the 9 storage nodes go completely offline.
- **Positive:** Minimizes storage overhead compared to raw 3x duplication.
- **Negative:** Requires CPU-intensive Reed-Solomon matrix multiplications during upload.

---

## ADR 004: In-Process Autonomous Agent Scheduling Fallback

### Context
The 25 autonomous agent loops (`app/agents/`) rely on Celery Beat. However, Celery Beat requires an independent, long-running daemon process that cannot be reliably deployed on free-tier hosting.

### Decision
Implement an **in-process APScheduler cron fallback** inside the FastAPI lifetime lifecycle context. If Celery is unavailable, the kernel spawns a non-blocking background thread that executes the agent loops directly.

### Consequences
- **Positive:** Ensures 100% agent execution consistency on simple single-container hosts.
- **Positive:** Wipes out the `agent_registry` 500 errors.
- **Negative:** Elevates memory consumption on the primary web-service container.
