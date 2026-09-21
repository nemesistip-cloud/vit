# VIT Ecosystem Production Sprint

## Phase 1 — Full Sports Data Audit

**Status:** Audit complete; implementation blocked until the application source is present in this repl
**Date:** 2026-08-07
**Scope:** The two sprint briefs uploaded to `attached_assets/`, the current repl contents, and a read-only inspection of the canonical VIT application repository used by the deployed gateway.

## Executive summary

The uploaded sprint documents correctly identify the highest-risk area: the Sports AI path mixes real provider integrations with neutral fallbacks, synthetic analytics, cached artifacts, and graceful empty responses. The deployed code has substantial sports infrastructure, but it is not yet safe to describe every generated prediction as grounded in live match data.

The current repl contains the two uploaded briefs only. It does not contain the VIT application source, package manifests, database configuration, or a workflow. Therefore no production code was changed and no local application could be started from this repl during Phase 1.

The canonical application repository inspected for this audit is:

- `https://github.com/nemesistip-cloud/vit`
- Branch inspected: `main`
- Relevant deployed service: `https://vitnetwork-nls4.onrender.com`

## Pipeline traced

```text
Frontend sports pages
  ↓
Gateway API
  ├── /api/matches
  ├── /api/predict
  ├── /api/sports
  ├── /api/analytics
  └── /api/inplay
  ↓
Ingestion and provider clients
  ├── football-data.org client
  ├── TheSportsDB client
  ├── iSports client
  └── odds provider client
  ↓
SQLAlchemy persistence
  ├── matches
  ├── predictions
  ├── odds snapshots
  ├── feature/history data
  └── fingerprints for deduplication
  ↓
Prediction and analytics services
  ├── feature builder
  ├── prediction route/orchestrator
  ├── model registry
  ├── analytics
  └── settlement/accountability services
```

## Verified implementation inventory

### Gateway routes

The gateway registers sports routes from `app/main.py`:

- `app/api/routes/matches.py`
  - Match listing
  - Upcoming matches
  - Live matches
  - Recent/completed matches
  - Match detail
  - Match analytics
  - Ensemble breakdown
  - League listing
  - Sync status
  - Fixture synchronization
- `app/api/routes/predict.py`
  - Prediction generation
  - Prediction response validation
  - Model-consensus calculation
  - Match insights
  - Accumulator generation
- `app/api/routes/sports.py`
  - Sports sync status
  - Fixture synchronization
  - Odds metadata synchronization
  - Competition listing
  - Provider listing
- `app/api/routes/analytics.py`
  - Summary
  - Model contribution
  - System analytics
  - User and validator leaderboards
  - Model performance aliases

### Persistence and deduplication

The `Match` model stores the core normalized fields required by the sprint:

- External fixture ID
- Home and away teams
- League
- Kickoff time
- Sport
- Status
- Source
- Fingerprint
- Scores and actual outcome
- Opening and closing odds

`app/data/match_dedup.py` provides a normalized fingerprint lookup and a legacy backfill helper. This is a useful foundation, but a live database audit is still required to confirm that all existing records have fingerprints and that no duplicate or orphan records remain.

### Ingestion and scheduling

`app/data/pipeline.py` contains recurring ingestion and odds-refresh loops:

- ETL startup loop
- Six-hour full ETL cadence
- Fifteen-minute odds refresh cadence
- Fourteen-day upcoming-fixture window
- Fixture upsert path
- Feature-store update path

The provider code includes normalization and mapping logic for fixtures, results, standings, teams, and head-to-head data.

## Confirmed risks and placeholder paths

### 1. Neutral prediction features can be produced without real history

Evidence:

- `app/services/predict_features.py`
  - Defines `_FALLBACK_FEATURES`.
  - Returns a full neutral feature set when the database is unavailable.
  - Uses neutral form and goal averages when a team has no historical matches.
  - Uses a neutral head-to-head split when no head-to-head history exists.
  - Logs `feature_completeness`, but the fallback path still returns data to downstream prediction code.

Impact:

Predictions can be numerically valid while not being grounded in real team history. This conflicts with the P0 requirement that the system return `status: waiting` instead of fake-looking values when a grounded prediction cannot be generated.

### 2. Analytics contains explicitly synthetic odds and mock form logic

Evidence:

- `app/services/vit_analytics.py`
  - Defines `synthetic_odds(...)`.
  - Contains a “Mock form logic for context” path.
  - Uses default market odds in prompt construction when real odds are absent.

Impact:

Analytics or AI prompts may present derived or default market values as if they were live bookmaker odds. This must be separated from real odds and labeled clearly, or withheld.

### 3. Fallback artifacts are present in the data tree

Evidence:

- `data/insights/match_10.json`
- `data/insights/match_12.json`
- `data/insights/match_15.json` through `match_25.json`
- `data/insights/match_123.json`

These artifacts include markers such as:

- `deterministic-fallback`
- `is_fallback: true`
- `Mocked analytics`

Impact:

Cached or pre-generated insight files can leak fallback content into production-facing flows unless read paths enforce provenance and freshness.

### 4. Provider failures commonly collapse into empty structures

Evidence:

- `app/services/football_api.py`
  - Returns `{}` for missing configuration, connection failures, forbidden keys, rate limits, and several HTTP errors.
  - Downstream methods convert missing response sections into empty lists or empty dictionaries.
- `app/services/predict_features.py`
  - Converts failed historical queries into empty collections and then neutral defaults.

Impact:

The system is resilient against crashes, but an unavailable provider can look like “no data” instead of a structured unavailable state. The frontend can therefore render empty states without exposing the actual cause or data freshness.

### 5. Frontend empty states are not yet proven against all sports contracts

Evidence:

- Sports pages call the match, prediction, analytics, and in-play APIs.
- In-play code intentionally renders “No live matches right now” when the API returns an empty list.
- The repository includes multiple API aliases and provider-specific routes.

Impact:

The route surface is broad, but Phase 1 cannot certify that every frontend expectation matches every backend schema without running the actual application and browser tests from the repl. This remains an explicit Phase 7 and Phase 8 validation item.

### 6. Test fixtures are not production data, but they can hide provenance gaps

The test suite contains dummy teams and mocked sessions for unit/integration testing. That is acceptable in tests, but production paths need stronger provenance assertions so test-style defaults cannot pass silently through runtime code.

## What was not yet verifiable

The following require the application source, runtime configuration, database access, or a running local workflow in this repl:

- Actual provider credentials and response freshness
- Current database fixture count
- Duplicate fixture count
- Orphan prediction count
- Stale-cache count
- Real upcoming fixture availability
- Prediction generation against a live fixture
- Real odds availability
- Live event/statistics updates
- Browser runtime errors and blank pages
- Mobile rendering
- End-to-end wallet regression
- Production health of every service

## Phase 1 acceptance result

| Requirement | Result |
|---|---|
| Trace frontend → gateway → prediction → provider → database → engine | Complete from source inspection |
| Identify mock matches and placeholder fixtures | Partial; explicit fallback artifacts found, runtime database not available |
| Identify dummy odds | Confirmed synthetic odds path |
| Identify fake or ungrounded predictions | Confirmed neutral-feature prediction path |
| Identify hardcoded teams | No production hardcoded-team path certified; test fixtures exist |
| Identify empty-array fallbacks | Confirmed provider/error paths and frontend empty states |
| Replace every placeholder with real data | Not started; blocked because app source is not in this repl |
| Document findings | Complete |

## Phase 2 entry plan

Before Phase 2 can go live:

1. Import the canonical VIT application source into this repl, preserving the uploaded briefs.
2. Add a reproducible local workflow and dependency installation path.
3. Add a provider abstraction with ordered providers, cached data, and a structured unavailable state.
4. Make normalized fixture provenance and freshness mandatory.
5. Stop prediction generation when the minimum real-data requirements are not met.
6. Replace silent `{}`/`[]` collapse with typed availability states and observable reasons.
7. Run ingestion against real provider responses and document the resulting live fixture count.

## Phase 1 deliverables

- Root causes discovered: documented above.
- Files modified: `docs/phase-1-sports-data-audit.md` only.
- APIs repaired: none; this phase was audit-only.
- Database fixes: none; the database is not present in this repl.
- Remaining technical debt: provider fallback semantics, synthetic analytics, fallback insight artifacts, runtime provenance, and missing local source/workflow.

**Phase 1 is complete as an audit. It is not a production-live phase because the application source and runtime are not yet present in this repl.**
