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
