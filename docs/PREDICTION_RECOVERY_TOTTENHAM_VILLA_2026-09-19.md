# Tottenham vs Aston Villa Prediction Recovery

**Fixture:** Tottenham Hotspur FC vs Aston Villa FC  
**Competition:** Premier League  
**Match ID:** `41`  
**External fixture:** `560587`  
**Chain:** `7764`

## Result

The fixture remains correctly blocked. No fabricated probabilities, statistics, injuries, odds, or historical matches were inserted. The production response renders successfully and reports:

- Evidence score: `51.7`
- Required threshold: `55.0`
- Feature completeness: `0.133`
- Recent completed history: one row per team
- Missing: comprehensive rolling team statistics and full recent form for both teams
- Prediction status: `failed`

## Root Causes

1. The deployed Football-Data.org credential returns HTTP `403`, so competition and team-history requests are unavailable.
2. TheSportsDB free endpoints are reachable but return only one recent team event and one recent league event, not enough for the required rolling history.
3. The recovered production database contains only one completed pre-kickoff result for either team. The remaining matching rows are future fixtures and cannot be used as evidence.
4. The prediction refresh path defaults to a 30-day TheSportsDB backfill, which cannot recover prior-season history at the start of a new season.
5. The rolling feature query did not consistently enforce a pre-kickoff cutoff, allowing future completed rows to be eligible if they existed.

## Verified Provider Checks

- Football-Data.org Premier League history: HTTP `403`, zero matches returned.
- Football-Data.org Tottenham team history: HTTP `403`, zero matches returned.
- Football-Data.org Aston Villa team history: HTTP `403`, zero matches returned.
- TheSportsDB Premier League season `2025-2026`: limited response, two target-team events.
- TheSportsDB `eventslast` for Tottenham and Aston Villa: one event each, dated 2026-09-12.
- TheSportsDB `eventspastleague`: one event returned.
- Odds: live freshness, one bookmaker, no multi-bookmaker consensus.

## Changes

- Added a `before` cutoff to rolling feature history queries.
- Passed the fixture kickoff boundary through match and prediction feature-generation call sites.
- Added regression coverage preventing future-match leakage.

The evidence threshold was not lowered and no fallback probabilities were promoted to a verified prediction.

The local recovery simulation subsequently reached `READY` with public history: 800 rows committed, 80 valid rows per target team, feature completeness `1.0`, and evidence score `60.0`. The real-model adapter was also corrected to call the implemented `ModelOrchestrator.predict` contract. Without configured provider odds, the model correctly refuses the real ensemble input and the system remains on the explicitly labeled neutral fallback; no synthetic odds are supplied.

## Market Intelligence Upgrade

- The Odds API Premier League key is `soccer_epl`; the configured request markets are `h2h,totals,spreads` with `eu,uk` regions and decimal odds.
- Odds API event timestamps now preserve both `last_update` and `commence_time`; materially future odds are rejected, with only a five-second clock-skew allowance.
- Fixture refresh now collects every complete bookmaker 1X2 snapshot available for the matched event, rather than one preferred bookmaker or a best-price composite.
- Consensus retains bookmaker count, median/minimum/maximum odds, raw margin, vig-free probabilities, dispersion, provider, event ID, and freshness.
- The shared provider registry lazily activates configured Odds API credentials and remains empty without credentials. No key is logged or exposed.
- Market features are passed separately from football-performance features and persisted in prediction provenance. Missing odds still block the real odds-dependent ensemble; synthetic odds are never generated.

The local environment currently has no `ODDS_API_KEY`, so live bookmaker retrieval for match `41` could not be attempted here. Production verification requires running the same flow with the configured secret and checking the returned event, bookmaker count, market set, timestamps, and quota headers.

## Recovery Execution Contract

The recovery runner must execute sources in this order:

1. Load and verify the persisted fixture identity and set the immutable cutoff to `2026-09-19T11:30:00Z`.
2. Fetch public Football-Data.co.uk Premier League season CSVs for `2627`, `2526`, and `2425`.
3. Normalize team names, dates, scores, completion state, statistics, and source metadata.
4. Reject rows on or after the cutoff, rows without a final score, and rows whose competition cannot be established.
5. Fetch TheSportsDB and other approved providers only as supplementary sources.
6. Deduplicate on `(competition, match_date, normalized_home, normalized_away)`; prefer the public season CSV for an exact duplicate, then prefer the source with the higher reliability class, otherwise retain the first complete record and log the conflict.
7. Upsert only validated rows in one database transaction. Commit after all rows and provenance checks pass; rollback the entire batch on any integrity or cutoff violation.
8. Rebuild features using only committed rows strictly before the cutoff and retain the source provider, URL, retrieval time, and transformation metadata for each contributing row.
9. Run the model, validate finite probabilities in `[0, 1]` summing to `1.0`, validate ensemble agreement, and evaluate evidence without changing the `55.0` threshold.
10. Persist a prediction only when evidence is sufficient; otherwise persist an explicit unavailable/failed result with missing elements and no probabilities.
11. Verify prediction status, audit/chain record, backend response, and frontend rendering before declaring success.

### Source acceptance and conflict rules

- Accepted historical rows require a final score, a parseable date, identifiable home and away teams, a completed status, and an attributable source URL or dataset identifier.
- Missing optional statistics remain `null`; they never receive defaults or values copied from another match.
- A source returning `403`, `401`, a CAPTCHA, a paywall, or a robots/access restriction is recorded as unavailable and is not retried through a bypass.
- Exact duplicate fixtures are counted once. Conflicting scores or dates are not silently merged: the conflict is logged, the higher-reliability accepted source wins only when its provenance is complete, and unresolved conflicts are excluded from model features.
- Public Football-Data.co.uk rows are classified as accepted high-confidence historical results. TheSportsDB rows are supplementary and cannot overwrite an exact public CSV row.

### Database write and rollback safety

- Public retrieval and normalization happen before any database write.
- Historical upserts use the fixture fingerprint and external ID when available; no existing result is deleted.
- A failed provider is isolated from successful providers, but a failed validation or transaction aborts the complete batch.
- Prediction creation starts in `INITIALIZING`; `READY` is written only after model, evidence, provenance, and probability validation succeeds.
- Insufficient evidence writes `FAILED`/unavailable metadata and zero or null prediction outputs; it never promotes neutral model defaults.
- Recovery and rerun operations must use a transaction boundary and log inserted, updated, skipped, conflicted, and rolled-back counts.

## Production Verification

- Gateway `/ping`: `200`
- Gateway `/health`: `200`, database connected
- Gateway `/readiness`: `200`
- Gateway `/deep-health`: `503` because Explorer is degraded; database healthy
- Real admin login: successful, role `admin`
- `/api/auth/me`: `200`
- Admin system health, metrics, users, models, audit log, and matches: `200`
- Invalid credentials: `401`
- Target fixture detail route: `200`, status remains `failed`

## Required Next Action

Restore a valid Football-Data.org subscription/key or connect an approved provider that supplies historical Premier League results and rolling team statistics. Then run the legitimate rerun endpoint, validate evidence >=55, persist the prediction, verify chain/audit recording, and confirm the frontend result. Until then, keeping this fixture unavailable is the correct production behavior.
