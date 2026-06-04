# VIT Architecture Upgrade: Team A - Core Platform & Data Architecture

## 1. Architecture Audit Report

### Current State (Pre-Refactor)
- **Unified Models:** The platform relied on the `Match` model for all prediction events, which was heavily sports-centric (home_team, away_team, goals).
- **Financial Infrastructure:** The `blockchain` module allowed staking and settlement on any `Match` record, regardless of its true nature.
- **Niche Markets:** Governance proposals and Election events existed as isolated entities without a common interface for predictions or automated mapping.

### Key Refactoring Decisions
- **Introduction of the `Market` Layer:** A new `Market` entity now serves as the parent for all predictable events. It classifies events as either `sports` or `niche`.
- **Match Decoupling:** `Match` records now belong to a `Market`. This allows for a clean separation between the event data (the "who and when") and the market logic (the "how it's traded").
- **Financial Segregation:** Staking (`UserStake`) is now explicitly linked to `Market`. The logic layer enforces a strict "No Sports Staking" policy to ensure legal and technical separation.

---

## 2. Updated Database Schema

### New Table: `markets`
| Column | Type | Description |
|--------|------|-------------|
| id | String(36) | Primary Key (UUID) |
| market_type | String(20) | `niche` or `sports` |
| category | String(50) | e.g., football, election, governance |
| title | String(255) | Display title |
| description| Text | Market details |
| status | String(50) | open, closed, settled, void |

### New Table: `market_mappings`
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary Key |
| internal_market_id | String(36) | Link to `markets.id` |
| provider_name | String(50) | e.g., Football-Data.org, Sportmonks |
| external_match_id | String(100) | Provider's event ID |
| external_selection_id| String(100) | Provider's market ID |

---

## 3. Market Classification System

Every predictable entity must now be associated with a `Market` entry.
- **Sports Markets:** Categories include football, basketball, etc. These act as analysis and affiliate-redirection infrastructure.
- **Niche Markets:** Categories include governance, elections, policy. These support full internal wallet functionality (staking, payouts).

---

## 4. Resolution Engine Documentation

### Current Pathways
1. **Oracle Settlement (Sports):**
   - Automated via `results_settler.py`.
   - Fetches scores from Football-Data.org or TheSportsDB.
   - Updates `Match` status to `settled`.
   - *Note:* In the new architecture, this updates the linked `Market` status but does NOT trigger VITCoin payouts if the market is `sports`.

2. **Blockchain Consensus (Niche):**
   - Orchestrated via `app/modules/blockchain/settlement.py`.
   - Requires an `OracleResult` to be submitted.
   - Triggers `settle_match` which calculates pools and pays winners.
   - *New Policy:* This path is restricted to markets where `market_type == "niche"`.

### Future Automation Recommendations
- **Smart Contract Resolution:** Implement bridge logic to pull election results from verifiable on-chain oracles (e.g., Chainlink Functions).
- **Decentralized Settlement:** Allow validators to vote on market outcomes for niche markets where no single truth source exists.
- **Automated Mapping:** Use the `market_mappings` table to automatically reconcile provider IDs during the ingestion phase to reduce manual admin overhead.
