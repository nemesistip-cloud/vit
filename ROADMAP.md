# Value Intelligence Trust (VIT) — System Roadmap
**Version:** 7.0.0
**Last updated:** 2026-05-18
**Purpose:** Handoff document for the next agent. Rebranding to VIT Ecosystem complete.

---

## 1. System Snapshot

| Layer | Technology |
|---|---|
| Backend | Python 3.11 / FastAPI 0.115 / SQLAlchemy 2.0 async (aiosqlite dev / asyncpg prod) |
| Database | SQLite (`vit.db`) in WAL mode (dev) — PostgreSQL via `DATABASE_URL` (prod) |
| Frontend | React 19 / TypeScript / Vite 6 / TailwindCSS 4 / ShadCN/Radix UI |
| State mgmt | `@tanstack/react-query` (server state) + `vitWS` WebSocket singleton |
| Agents | 22 autonomous agents via `BaseAgent` + `SwarmOrchestrator` (30s heartbeat supervisor) |
| ML | 13 models loaded at startup (6 base + 6 v2 + 1 ensemble) |
| Auth | JWT (access/refresh) + TOTP 2FA + JWT blocklist (`token_blocklist` table) |
| Payments | Stripe (USD), Paystack (NGN), USDT, Pi Network, VITCoin |
| Chain | VIT-Chain sovereign hash-linked ledger (`vit_chain_ledger.db`, PoW difficulty=4) |
| Startup | `bash scripts/start_fullstack.sh` → uvicorn port 8000 + Vite port 5000 |

**Health check:** `GET /health` → `{"status":"ok","version":"7.0.0","models_loaded":13,"agents":{"total":22,"running":22}}`

---

## 2. Environment & Secrets

### Configured (valid)
| Secret | Status | Notes |
|---|---|---|
| `JWT_SECRET_KEY` | ✅ Configured | Valid |
| `SECRET_KEY` | ✅ Configured | Flask/session secret |
| `GEMINI_API_KEY` | ✅ Valid (`AIza…`) | Primary AI provider — available |
| `OPENAI_API_KEY` | ✅ Valid (`sk-p…`) | Secondary AI provider — available |
| `FOOTBALL_DATA_API_KEY` | ✅ Configured | Blocked at network level (see below) |
| `PAYSTACK_SECRET_KEY` | ✅ Configured | Valid |
| `STRIPE_SECRET_KEY` | ⚠️ Suspect prefix (`mk_1…`) | Not a standard `sk_live_` / `sk_test_` key — checkout will fail |
| `TELEGRAM_BOT_TOKEN` | ✅ Configured | Valid |
| `ADMIN_PASSWORD` | ✅ Configured | Do not hardcode |
| `ODDS_API_KEY` | ✅ Configured | Used by odds router; returns 503 without valid key |

### Invalid / Missing (action required)
| Secret | Status | Impact |
|---|---|---|
| `CLAUDE_API_KEY` | ❌ 3-char placeholder (`Key`) | Claude always fails auth → 30-min backoff |
| `XAI_API_KEY` | ❌ 3-char placeholder (`Key`) | Grok always fails auth → 30-min backoff |
| `RESEND_API_KEY` | ❌ Missing | Email notifications disabled (password reset, verification broken) |
| `DATABASE_URL` | ⚠️ Not set in dev | Defaults to SQLite — set for production PostgreSQL |
| `VAULT_MASTER_KEY` | ⚠️ Not set | TMA vault uses base64 fallback — set for production security |

**To fix:** Replace `CLAUDE_API_KEY` and `XAI_API_KEY` with real keys in Replit Secrets. The 30-min backoff on invalid keys is silent (no crash) but disables those providers.

### Network Constraint (Replit sandbox)
`api.football-data.org:443` is **TCP-blocked** at the Replit network level. DNS resolves but all connections time out. The system handles this gracefully:
- Match fixtures: 159 records seeded via internal pipeline
- Settlement: attempts Football-Data.org first, falls back to TheSportsDB (free, always available)
- Circuit breaker in `results_settler.py`: 10-min skip window after first `ConnectTimeout`
- This is **not an API key issue** — it is a sandbox network restriction

---

## 3. Database State (as of 2026-05-13)

| Table | Rows | Status |
|---|---|---|
| `users` | 1 | Admin only; no real users yet |
| `matches` | 159 | Real team names; seeded from pipeline |
| `predictions` | 330 | All settled — seeded synthetically |
| `wallets` | 1 | Admin wallet only |
| `model_metadata` | 13 | All 13 models registered (v1+v2+ensemble) |
| `subscription_plans` | 3 | Basic / Pro / Elite seeded |
| `platform_configs` | 12 | Config defaults seeded |
| `vitcoin_price_history` | 7 | Price history seeded |
| `node_activities` | 167 | Agent activity recorded |
| `network_snapshots` | 5 | Network state snapshots |
| `vit_identities` | 22 | W3C DID docs for all 22 agents |
| `verifiable_credentials` | 14 | VCs for agents and models |
| `agent_insights` | 44 | AI agent insight reports |
| `pipeline_runs` | 6 | ETL pipeline run history |
| `marketplace_listings` | 12 | 12 system ML models listed |
| `validator_profiles` | 1 | Admin registered as active validator |
| `tasks` | 8 | Gamification tasks seeded |
| `task_categories` | 3 | Prediction / Social / Learning |
| `bankroll_states` | 5 964 | Kelly criterion states tracked |

### Empty tables (feature complete, no live data yet)
| Table | Feature | Blocker |
|---|---|---|
| `oracle_results` | Oracle consensus output | No live settled matches from external API |
| `match_settlements` | Settlement pipeline | Football-Data.org TCP-blocked in sandbox |
| `consensus_predictions` | Oracle aggregation | Depends on `oracle_results` |
| `clv_entries` | Closing Line Value tracking | Needs live odds + settled matches |
| `model_performances` | ML accuracy metrics | Needs live settled predictions from real API |
| `training_jobs` | ML retraining pipeline | Needs 50+ settled predictions; no jobs triggered yet |
| `notifications` | In-app + push | No real events to trigger them |
| `gov_proposals` / `gov_votes` | DAO governance | No proposals created |
| `bridge_transactions` | Cross-chain bridge | Not used |
| `audit_logs` | Admin audit trail | No admin actions logged yet |

---

## 4. Known Bugs & Incomplete Implementations

### 4.1 Stripe payment key invalid
`STRIPE_SECRET_KEY` starts with `mk_1…` which is not a standard Stripe key format. Subscription checkout (`/subscription/create-checkout`) will fail silently at payment intent creation.

**Fix:** Get a valid `sk_test_…` key from the Stripe dashboard and update the Replit Secret.

### 4.2 Email disabled (no Resend key)
`app/services/alerts.py` and all email routes (`/auth/forgot-password`, `/auth/send-verification`, `/auth/verify-email`) require `RESEND_API_KEY`. Without it, transactional email is completely disabled.

**Fix:** Create a free Resend account at resend.com, generate an API key, and add it to Replit Secrets.

### 4.3 CLV tracking empty
`clv_entries` = 0 rows. CLV is computed at settlement time from `Match.closing_odds_*` columns. The columns exist on `Match` records but odds data has never been populated (Odds API returns 503 without a valid key, Football-Data.org is blocked).

**Fix:** Supply a valid `ODDS_API_KEY` so the odds refresh agent can fill closing odds. CLV will then populate automatically as matches settle.

### 4.4 Model performance metrics empty
`model_performances` = 0 rows. The `performance-monitor` agent runs every 30 min (90s initial delay) and calls `rolling_window_accuracy()`. This was fixed (join now uses `cast(Match.id, String) == AIPredictionAudit.match_id`), but `ai_prediction_audits` table has no records yet because no live predictions have been made through the API (predictions are seeded synthetically, not via the inference endpoint).

**Fix:** Once real users make predictions through the app (calling `POST /predict/{match_id}`), the audit records will populate and the performance monitor will track accuracy.

### 4.5 Results settlement errors in sandbox
The `results_settler.py` settlement loop was previously crashing for all 21 match attempts with `sqlalchemy.exc.MissingGreenlet`. This is now fixed (session uses `expire_on_commit=False`). However, settlement still produces 0 results because Football-Data.org is TCP-blocked and TheSportsDB fallback only has historical matches that don't match the fixture IDs in the DB.

**Fix (long-term):** Seed a dedicated batch of matches with known final scores, then trigger settlement manually via `POST /admin/settle` to verify the full pipeline end-to-end.

---

## 5. Completed Work

### Session 5 — Rebranding to Value Intelligence Trust (VIT)
- **Visual Identity**: Deployed new palette (#050505, #1E6BFF, #00C896, #C0C7D1) and Space Grotesk typography.
- **Brand Assets**: Created and integrated programmatic `BrandLogo` with "triangular_neural_v" symbolism.
- **Centralization**: All brand strings (Name, Tagline, Mission) moved to `app/config.py` and exposed via API.
- **System-wide Integration**: Rebranded 50+ frontend pages and all backend services (Email, Telegram, Alerts).
- **Core Narrative**: Shifted from sports-only focus to "Programmable Trust" and "Value, Intelligence, and Trust" ecosystem.

### Session 1 — Initial setup
- Puter.js multi-account panel (`ai-sources.tsx`, `puter-ai.ts`)
- `isPuterSignedIn`/`puterSignIn`/`puterSignOut`/`getPuterUser` exports
- DELAY_MS raised to 3500ms in agent loop
- Rate-limit detection with 15s cooldown
- JWT-based rate limiter keying with raised limits

### Session 2 — Top 10 bug fixes
1. Grok model names corrected: `grok-2`/`grok-beta` → `grok-3-mini`/`grok-2-1212`
2. Provider 30-min backoff on 401/403 auth failures
3. Claude + Grok model loops `break` on auth failures
4. Match sync error logging uses `repr(e)` + exception type (was silent)
5. Misleading `pip install sports-skills` startup message removed
6. Vite startup duplicate `--host --port` flags removed
7. Odds anomaly agent's private `_call_grok` → shared `call_ai` cascade
8. News sentinel logs when scraper returns empty
9. `ai_support.py` replaced Gemini-only `_call_gemini` with `call_ai` cascade
10. `/api/support/status` now reports per-provider availability

### Session 3 — Research tab + model upgrade
1. EV Scanner status codes fixed (`app/modules/quant/routes.py`): added `"upcoming"`, `"scheduled"`, `"live"`, `"in_play"` to match DB values
2. `grok_insights.py` upgraded to use shared `call_ai()` cascade with markdown fence stripping
3. `StrategyPanel` empty-state fixed (`research.tsx`): added `data.error` guard
4. Synthetic predictions seeded: 15 predictions (9 settled) for quant panel data

### Session 4 — V6 upgrade + route audit
1. `APP_VERSION` updated: `"5.0.0"` → `"6.0.0"` in `app/config.py` (single source of truth for `/health` and startup banner)
2. `/system/status` flat field aliases added (`main.py`): `total_users`, `active_users_30d`, `active_validators`, `total_staked_vit` now present at top level (ecosystem ticker was reading flat fields but endpoint only returned nested structure)
3. Ecosystem ticker price field fixed (`ecosystem-ticker.tsx`): was reading `price?.price_usd` but backend returns `price?.price` — changed to `price?.price ?? price?.price_usd` for forward compatibility
4. `rolling_window_accuracy` join fixed (`app/services/accuracy_enhancer.py`): was joining `Match.external_id == AIPredictionAudit.match_id` but the orchestrator stores the integer match ID as a string — corrected to `cast(Match.id, String) == AIPredictionAudit.match_id`
5. Results settler `MissingGreenlet` crash fixed (`app/services/results_settler.py`): after each `await db.commit()` in the loop, SQLAlchemy expired all loaded `Match` attributes causing a lazy-load attempt that fails in async context — fixed with `db.sync_session.expire_on_commit = False`
6. Full route audit completed: all 57 frontend pages verified against backend endpoints — all API paths are correctly registered and matched

---

## 6. Priority Work Queue (next agent)

### P0 — Fix immediately (broken user-facing features)

**P0-A: Replace Stripe key**
- Current `STRIPE_SECRET_KEY` has prefix `mk_1…` — not a valid Stripe key format
- Subscription checkout will fail silently at payment intent creation
- Get a `sk_test_…` key from Stripe dashboard and update the Replit Secret

**P0-B: Add Resend API key for email**
- Password reset, email verification, and notification emails are completely non-functional
- Create a free Resend account → generate API key → add as `RESEND_API_KEY` in Replit Secrets

### P1 — High value (significant UX improvement)

**P1-A: Seed real (or more) settled matches for the performance pipeline**
- `model_performances`, `clv_entries`, and `ai_prediction_audits` are all empty because the settlement pipeline has never run successfully against matching fixtures
- Option A: Insert a batch of 20–30 matches with known outcomes directly into the DB, then call `POST /admin/settle` to exercise the full settlement → CLV → performance pipeline
- Option B: Switch match data source to an API not blocked in the Replit sandbox (e.g., `api-football.com` free tier or TheSportsDB)

**P1-B: Supply real Claude and Grok API keys**
- Both providers are currently placeholder 3-char strings → permanent 30-min backoff
- This halves the effective AI capacity (Gemini + OpenAI work, Claude + Grok never tried)
- Replace `CLAUDE_API_KEY` and `XAI_API_KEY` in Replit Secrets

### P2 — Medium priority (feature completeness)

**P2-A: Populate closing odds via Odds API**
- `ODDS_API_KEY` is configured but the odds refresh agent returns 503 if the key is invalid
- Valid odds data is required for CLV calculation and the arbitrage/comparison pages
- Verify the key is active at the-odds-api.com

**P2-B: Trigger first ML retraining job**
- `training_jobs` = 0; `retrain_trigger` agent runs every 12h but threshold check may block it
- Manually trigger via `POST /admin/training/trigger` once 50+ settled predictions exist
- Review `app/agents/retrain_trigger.py` for the minimum-sample threshold

**P2-C: Create first governance proposal**
- DAO governance UI is complete (`/governance`) but has no proposals
- Creating one proposal as seed data would exercise the full vote → execute pipeline
- Use admin account via `POST /api/governance/proposals`

### P3 — Nice to have (polish)

**P3-A: Redis caching** ✅ Done
- `app/services/cache.py` uses Redis primary + in-memory fallback; applied to key endpoints

**P3-B: Production deployment prep**
- Set `DATABASE_URL` to a real PostgreSQL instance
- Set `VAULT_MASTER_KEY` for AES-256-GCM TMA vault encryption (currently base64 fallback)
- Set `ENVIRONMENT=production` to enable ML model loading at startup
- Run `alembic upgrade head` before first production start

**P3-C: Bridge & governance data**
- `bridge_transactions` = 0, `gov_proposals` = 0
- Both features have complete UIs that gracefully show empty states
- No code changes needed; data will appear with real usage

---

## 7. Architecture Reference

### Router registration (main.py lines 1824–1994)
All routers are registered. Key prefixes:
| Prefix | Router file |
|---|---|
| `/api/agents` | `app/api/routes/agents.py` |
| `/api/ai-engine` | `app/modules/ai/routes.py` |
| `/api/ai-upload` | `app/api/routes/ai_upload.py` |
| `/api/bankroll` | `app/api/routes/bankroll.py` |
| `/api/bridge` | `app/modules/bridge/routes.py` |
| `/api/cashout` | `app/modules/betting/cash_out_sentinel.py` |
| `/api/chain` | `vit_chain.py` (VIT-Chain ledger) |
| `/api/contracts` | `app/modules/smart_contracts/routes.py` |
| `/api/developer` | `app/modules/developer/routes.py` |
| `/api/did` | `app/modules/did/routes.py` |
| `/api/governance` | `app/modules/governance/routes.py` |
| `/api/identity` | `app/modules/identity/routes.py` |
| `/api/kyc` | `app/modules/kyc/routes.py` |
| `/api/leaderboard` | `app/api/routes/dashboard.py` |
| `/api/marketplace` | `app/modules/marketplace/routes.py` |
| `/api/merit` | `app/modules/merit/routes.py` |
| `/api/models` | `app/api/routes/model_performance.py` |
| `/api/network` | `app/modules/network/routes.py` |
| `/api/oracle` | `app/modules/blockchain/oracle.py` |
| `/api/referral` | `app/modules/referral/routes.py` |
| `/api/rewards` | `app/modules/rewards/routes.py` |
| `/api/security` | `app/modules/security/routes.py` |
| `/api/stats` | `app/api/routes/stats.py` |
| `/api/tasks` | `app/modules/tasks/routes.py` |
| `/api/tma` | `app/modules/telegram_mini_app/integration.py` |
| `/api/treasury` | `app/modules/treasury/routes.py` |
| `/api/trust` | `app/modules/trust/routes.py` |
| `/api/wallet` | `app/modules/wallet/routes.py` |
| `/auth` | `app/auth/verification.py` + `app/auth/totp.py` |
| `/admin` | `app/api/routes/admin.py` |
| `/analytics` | `app/api/routes/analytics.py` |
| `/subscription` | `app/api/routes/subscription.py` |
| `/training` | `app/api/routes/training.py` |

### SwarmOrchestrator vs AgentCoordinator
- `app/core/swarm_orchestrator.py` supervises all 22 agents with per-agent restart tracking
- `app.state.agent_coordinator` is kept as an alias for legacy routes
- Health endpoint reads from `swarm.health_summary()`
- All 22 agents start in sequence at startup (~30–35s total boot time)

### AI cascade order
1. **Chat** (`gemini_chat.py`): Gemini → Claude → Grok on 429/error
2. **Analysis** (`multi_ai_dispatcher.py`): fans out to all 4 providers in parallel; `scie.py` is statistical fallback
3. **Insights** (`claude_insights.py`, `openai_insights.py`, `gemini_insights.py`, `grok_insights.py`): all use `call_ai()` from `app/services/ai_client.py`
4. Per-provider timeout: 20s. Backoff on 401/403: 30 min. Backoff on 429: 8s.

---

## 8. File Quick-Reference

### Backend — Key files
| File | Purpose |
|---|---|
| `main.py` | App startup, 530+ routes, all router mounts, lifespan hooks |
| `app/config.py` | `APP_VERSION = "6.0.0"` and all module-level config vars |
| `app/db/models.py` | All SQLAlchemy ORM models |
| `app/db/database.py` | `AsyncSessionLocal`, `get_db`, SQLite WAL config |
| `app/core/swarm_orchestrator.py` | Supervises all 22 agents, 30s heartbeat |
| `app/services/ai_client.py` | Shared `call_ai()` cascade: Gemini→Claude→OpenAI→Grok |
| `app/services/results_settler.py` | Match settlement — `expire_on_commit=False` fix applied |
| `app/services/accuracy_enhancer.py` | `rolling_window_accuracy()` — join fix applied |
| `vit_chain.py` | VIT-Chain sovereign ledger (hash-linked SQLite) |
| `app/modules/betting/cash_out_sentinel.py` | Momentum-based auto cash-out engine |
| `app/modules/telegram_mini_app/integration.py` | TMA initData auth + vault + metering |
| `app/api/middleware/auth.py` | `APIKeyMiddleware` — JWT + API key auth, `_PUBLIC_SUBPATHS` list |
| `app/api/routes/admin.py` | Full admin panel backend (~3 800 lines) |
| `app/api/routes/training.py` | ML training pipeline endpoints |
| `app/modules/wallet/routes.py` | Wallet + KYC + admin KYC endpoints |
| `alembic/versions/` | 17 migrations; latest: `e5f6a7b8c9d0` (v6 schema) |

### Frontend — Key files
| File | Purpose |
|---|---|
| `frontend/src/App.tsx` | All 57 routes, lazy imports, auth wrappers |
| `frontend/src/api-client/index.ts` | Central `API` constants object — all route strings |
| `frontend/src/lib/auth.tsx` | `useAuth()`, JWT storage, token refresh |
| `frontend/src/lib/apiClient.ts` | `apiGet`/`apiPost` — prepends `/api` to all paths |
| `frontend/src/components/ecosystem-ticker.tsx` | Price ticker — uses `price?.price` field |
| `frontend/src/pages/admin.tsx` | Full admin dashboard (~3 200 lines) |
| `frontend/src/pages/training.tsx` | ML training job board |
| `frontend/src/pages/agents.tsx` | Agent monitor (`/api/agents/status`) |
| `scripts/start_fullstack.sh` | Startup script (backend port 8000 + frontend port 5000) |
| `scripts/start_production.sh` | Production: builds `frontend/dist`, then gunicorn on :5000 |

---

## 9. Coding Conventions

- **Database:** Always use `AsyncSession` from `app.db.database.get_db`. For background tasks that loop and commit, set `session.sync_session.expire_on_commit = False` to prevent lazy-load errors after each commit.
- **Config:** Read env vars via `os.getenv()` — no `settings` object. `APP_VERSION` lives in `app/config.py`.
- **AI calls:** Always use `call_ai()` from `app.services.ai_client` — never add new isolated `httpx` clients to provider APIs.
- **Auth:** Protected endpoints use `Depends(get_current_user)`. Admin endpoints additionally check `current_user.role == "admin"`.
- **Match status values:** Always lowercase: `upcoming`, `scheduled`, `live`, `in_play`, `completed`, `finished`. Never use Football-Data.org uppercase codes inside the app.
- **Error logging:** Use `repr(e)` and `type(e).__name__` — `str(e)` is often empty for network exceptions.
- **Frontend API calls:** `apiGet("/some/path")` prepends `/api` automatically → becomes `/api/some/path`. Paths in `API` constants in `api-client/index.ts` already include `/api/`.
- **AIPredictionAudit.match_id:** Stored as `str(integer_match_id)` — join to `Match` using `cast(Match.id, String)`, not `Match.external_id`.
- **main.py:** ~100KB — read in sections using `offset`/`limit`. Router registrations are at lines 1824–1994.

---

## 10. Running the App

```bash
# Development (backend :8000 + frontend :5000)
bash scripts/start_fullstack.sh

# Production (builds frontend first, then serves everything on :5000)
bash scripts/start_production.sh

# Health check
curl http://localhost:8000/health

# Get admin JWT (for API testing)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@vit.network","password":"<ADMIN_PASSWORD>"}'

# Test a protected endpoint
curl http://localhost:8000/api/agents/status \
  -H "Authorization: Bearer <token>"
```

The Replit workflow `Start application` runs `bash scripts/start_fullstack.sh` automatically. Backend takes ~30–35s to boot (22 agents + migrations + seeding) before accepting connections.
