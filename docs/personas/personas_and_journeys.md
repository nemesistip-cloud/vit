# VIT Network — Persona Architecture & Journey Maps

**Version:** 6.0.0
**Domain:** /docs/personas/
**Status:** Approved Reference

---

## 1. Purpose & Scope

To design a scalable, unified digital ecosystem, we must understand the diverse range of actors interacting with the VIT Network. This document defines the **13 distinct Personas** that span the consumer, enterprise, developer, and agentic layers of the system. For each persona, we specify their goals, system permissions (RBAC), daily workflows, and journey maps.

---

## 2. Global Persona Permission Matrix (RBAC)

The personas are mapped to backend roles to enforce secure access boundaries:

| Persona | Role Code | API Access Levels | Primary Workspaces |
| :--- | :--- | :--- | :--- |
| **Guest** | `guest` | Read-only public endpoints | Home, Platform, Status |
| **Individual** | `user` | standard user endpoints | Wallet, Sports Intel, Assistant |
| **Professional** | `user` | standard user, high quota | Sports Intel, Finance Intel |
| **Business** | `business` | business analytics API | Enterprise, Wallet, Analytics |
| **Enterprise** | `business` | full enterprise API, multi-seat | Enterprise, Cloud, Storage, Identity |
| **Developer** | `developer` | API management, webhook registry | Developer Platform, Cloud |
| **Creator** | `creator` | signal sales API, profile listing | Marketplace, Identity |
| **Researcher** | `analyst` | telemetry analytics, simulation runs | Analytics, AI Assistant |
| **Validator** | `validator` | consensus voting, slashing appeals | Governance, Analytics |
| **DAO Member** | `voter` | voting on-chain, proposal triggers | Governance |
| **Administrator**| `admin` | administrative endpoints, config | Admin, Settings, Analytics |
| **Moderator** | `moderator` | dispute resolution, review logs | Admin, Settings |
| **AI Agent** | `agent` | automated machine-to-machine API | Automation, Developer Platform |

---

## 3. Detailed Persona Specifications

### 3.1 Guest
- **Goals:** Understand the platform's accuracy and performance before signing up.
- **Pain Points:** Reluctance to register without verifying on-chain transparency.
- **Permissions:** Read-only access to `/api/sports/competitions` and `/api/status`.
- **Daily Workflow:** Visits home page, inspects the live status of the 13-model ensemble, views transaction gas charts.
- **Journey Map:**
  `Visits Landing Page` $\rightarrow$ `Inspects Status Page` $\rightarrow$ `Reads Docs` $\rightarrow$ `Clicks Register`

### 3.2 Individual
- **Goals:** Place small, highly accurate sport bets using the 13-model AI consensus predictions.
- **Pain Points:** Lack of sports analytics expertise; slow conversion between fiat and stablecoins.
- **Permissions:** Full standard consumer access.
- **Daily Workflow:** Checks `/api/matches/upcoming`, views predicted score matrix, converts NGN/USD to VITCoin, and places stake.
- **Journey Map:**
  `Logs In` $\rightarrow$ `Navigates to Dashboard` $\rightarrow$ `Views Match Probs` $\rightarrow$ `Converts stablecoin` $\rightarrow$ `Executes Stake`

### 3.3 Professional
- **Goals:** Execute large prediction arb trades across external sportsbooks and the VIT platform.
- **Pain Points:** Limits on API call sizes; delayed closing-line-value (CLV) histories.
- **Permissions:** High-rate-limit consumer APIs.
- **Daily Workflow:** Pulls down fair-value odds via CSV export, tracks model calibration graphs, registers webhook for odds changes.
- **Journey Map:**
  `Authenticates` $\rightarrow$ `Launches Analytics Studio` $\rightarrow$ `Compares Fair Lines` $\rightarrow$ `Submits API Arbitrage orders`

### 3.4 Business
- **Goals:** Offer prediction metrics or marketplace listings to a localized customer base.
- **Pain Points:** High card-processing fees; lack of white-label analytics.
- **Permissions:** Merchant/Business API layers.
- **Daily Workflow:** Monitors active user referrals, reviews payout balances, configures local payment gateways (Paystack/Stripe).

### 3.5 Enterprise
- **Goals:** Utilize Tachyon swarm storage and cloud orchestrator to host high-security enterprise databases.
- **Pain Points:** Strict data compliance laws (GDPR/NDPR); downtime risks.
- **Permissions:** High-volume cloud deployment access.
- **Daily Workflow:** Deploys virtual server templates, monitors fragment replication safety metrics, audits developer keys.

### 3.6 Developer
- **Goals:** Integrate the Python SDK or JSON-RPC endpoints into proprietary algorithmic software.
- **Pain Points:** Outdated API documentation; unhelpful 500 error messages.
- **Permissions:** Developer dashboard access, key generation.
- **Daily Workflow:** Generates access keys, registers webhook URL, runs integration test suites, reads endpoint specifications.

### 3.7 Creator
- **Goals:** Build and monetize accurate intelligence signals on the P2P Marketplace.
- **Pain Points:** High platform commissions; unfair buyer dispute claims.
- **Permissions:** P2P listing and signal sales.
- **Daily Workflow:** Posts new prediction picks, responds to user questions, reviews earned VITCoin withdraw balance.

### 3.8 Researcher
- **Goals:** Run Monte Carlo simulations and test custom ML models against the historical dataset.
- **Pain Points:** Data access throttles; slow job execution times.
- **Permissions:** High-performance model simulation and training triggers.
- **Daily Workflow:** Uploads training CSV datasets, registers new training runs, tracks accuracy calibration graphs.

### 3.9 Validator
- **Goals:** Maintain high uptime and earn validator block-consensus rewards.
- **Pain Points:** Sudden slashing events due to transient cloud network disconnects.
- **Permissions:** Block validation signing.
- **Daily Workflow:** Checks node sync status, monitors storage challenge pings, votes on active consensus proposals.

### 3.10 DAO Member
- **Goals:** Vote on critical network changes, treasury allocations, and validator appeals.
- **Pain Points:** Low voting turnouts; complex on-chain signature ceremonies.
- **Permissions:** On-chain proposal voting.
- **Daily Workflow:** Reviews proposal queue, checks locked voting stake, casts secp256k1 signed votes.

### 3.11 Administrator (Genesis Admin)
- **Goals:** Ensure platform uptime, configure security constraints, and manage payment configurations.
- **Pain Points:** Critical 500 errors; manual database migration steps.
- **Permissions:** Super admin root access (RBAC).
- **Daily Workflow:** Reviews audit logs, configures platform secrets, monitors server hardware latency.

### 3.12 Moderator
- **Goals:** Mitigate disputes in the P2P marketplace and review flagged user accounts.
- **Pain Points:** High volumes of malicious chargeback or scam reports.
- **Permissions:** Dispute moderation and user flagging.
- **Daily Workflow:** Reviews unresolved escrow disputes, inspects user audit logs, suspends fraudulent addresses.

### 3.13 AI Agent
- **Goals:** Autonomously fetch prediction parameters, execute trades, and manage storage quotas.
- **Pain Points:** Session token expiries (requires long-lived API keys).
- **Permissions:** Machine-to-machine API tokens.
- **Daily Workflow:** Continuously queries matches, analyzes arbitrage paths, triggers storage backups, and registers results.

---

## 4. End-to-End Persona Interaction Scenario

To demonstrate the cohesive operation of these 13 personas, consider the following scenario in a fully booted VIT Network:

```
[Developer] registers a prediction app using the API.
  └── [AI Agent] queries matches via the Developer's portal.
        └── [Researcher] trains a model on historical data.
              └── [Validator] signs the consensus blocks.
                    └── [DAO Member] votes on the transaction fee distribution.
                          └── [Genesis Admin] monitors the entire event through the dashboard.
```

By specifying these rich persona profiles, the VIT Network UI/UX is built with extreme precision, avoiding the common failure of designing generic interfaces for a highly specialized user base.
