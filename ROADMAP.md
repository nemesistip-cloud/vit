# VIT Sports Intelligence Network — System Roadmap
**Version:** 4.7.5  
**Last updated:** 2026-05-03  
**Purpose:** Handoff document for the next agent. Read this before doing any work.

---

## 1. System Snapshot

| Layer | Technology |
|---|---|
| Backend | Python 3.11 / FastAPI 0.115.6 / SQLAlchemy (aiosqlite) |
| Database | SQLite (`vit.db`) in WAL mode — PostgreSQL for production |
| Frontend | React 19 / TypeScript / Vite / TailwindCSS 4 / ShadCN UI |
| State mgmt | `@tanstack/react-query` (server state) + `vitWS` WebSocket singleton |
| Agents | 22 autonomous agents via `BaseAgent` + coordinator |
| ML | 12 models (6 base + 6 v2) loaded at startup |
| Auth | JWT (access/refresh) + TOTP 2FA |
| Startup | `bash scripts/start_fullstack.sh` → uvicorn port 8000 + Vite port 5000 |

**Health check:** `GET /health` → `{"status":"ok","models_loaded":12,"db_connected":true}`

---

## 2. Environment & Secrets

### Configured (valid)
| Secret | Status | Notes |
|---|---|---|
| `JWT_SECRET_KEY` | ✅ 64 chars | Valid |
| `GEMINI_API_KEY` | ✅ 39 chars (`AIza…`) | Valid format; primary AI provider |
| `OPENAI_API_KEY` | ✅ 164 chars (`sk-p…`) | Valid project key |
| `FOOTBALL_DATA_API_KEY` | ✅ 32 chars | Valid — but see Network Constraint below |
| `PAYSTACK_SECRET_KEY` | ✅ 48 chars | Valid |
| `TELEGRAM_BOT_TOKEN` | ✅ 46 chars | Valid |
| `REDIS_URL` | ✅ 107 chars | Configured; caching integration may be incomplete |
| `ADMIN_EMAIL` | ✅ `admin@vit.network` | |
| `ADMIN_PASSWORD` | ✅ 11 chars | Set via env; do not hardcode |
| `STRIPE_SECRET_KEY` | ⚠️ 27 chars (`mk_1…`) | Unusual prefix — verify it is a valid Stripe key |

### Invalid / Missing (need fixing)
| Secret | Status | Impact |
|---|---|---|
| `CLAUDE_API_KEY` | ❌ 3 chars (`Key`) | Placeholder — Claude always fails auth → 30-min backoff |
| `XAI_API_KEY` | ❌ 3 chars (`Key`) | Placeholder — Grok always fails auth → 30-min backoff |
| `RESEND_API_KEY` | ❌ MISSING | Email notifications (`/email/*`) are completely broken |

**To fix:** Replace `CLAUDE_API_KEY` and `XAI_API_KEY` in Replit Secrets with real keys, or leave as-is (the 30-min backoff means they are skipped cleanly — no crash). Add `RESEND_API_KEY` to enable email.

### Network Constraint (Replit sandbox)
`api.football-data.org:443` is **TCP-blocked** at the Replit network level. DNS resolves but all connections timeout. The system runs fully in offline mode:
- Match data: synthetic fixtures with real team names
- FT results: simulated via `app/services/ft_backfill.py`
- Circuit breaker: 10-min skip after first ConnectTimeout (`results_settler.py`)
- This is **not an API key issue** — it is a sandbox restriction.

---

## 3. Database State (as of 2026-05-03)

| Table | Rows | Status |
|---|---|---|
| `users` | 1 | Admin only; no real users yet |
| `matches` | 15 | All synthetic (`source=synthetic`) |
| `predictions` | 15 | 9 settled (was_correct set), 6 open — seeded synthetically |
| `wallets` | 1 | Admin wallet only |
| `model_metadata` | 12 | 12 models registered |
| `subscription_plans` | 3 | Basic / Pro / Elite seeded |
| `platform_configs` | 11 | Config defaults seeded |
| `vitcoin_price_history` | 5 | Price history seeded |
| `node_activities` | 106 | Agent activity recorded |
| `network_snapshots` | 3 | Network state snapshots |
| `vit_identities` | 22 | W3C DID docs for 22 agents |
| `verifiable_credentials` | 12 | VCs for 12 models |
| `agent_insights` | 25 | AI agent insight reports |
| `audit_logs` | 5 | Admin audit trail |
| `pipeline_runs` | 4 | ETL pipeline run history |

### Empty tables (feature exists, no data yet)
| Table | Feature | Blocker |
|---|---|---|
| `oracle_results` | Oracle consensus output | No settled matches from live API |
| `match_settlements` | Settlement pipeline | Football API network-blocked |
| `consensus_predictions` | Oracle aggregation | Depends on oracle_results |
| `clv_entries` | Closing Line Value tracking | Needs settled match data |
| `model_performances` | ML accuracy metrics | Needs predictions + settlements |
| `marketplace_listings` | Model marketplace | No listings submitted |
| `validator_profiles` | Validator system | No validators registered |
| `tasks` / `task_categories` | Gamification tasks | Not seeded |
| `bankroll_states` | Wallet bankroll tracking | Not initialized |
| `training_jobs` | ML retraining | No jobs triggered |
| `notifications` | In-app + push notifications | No events to fire them |
| `gov_proposals` / `gov_votes` | DAO governance | No proposals created |
| `bridge_transactions` | Token bridge | Not used |

---

## 4. Known Bugs & Broken Endpoints

### 4.1 Broken API Endpoints (404s)
The frontend calls these paths but they return 404:

| Frontend Call | Why it 404s | Fix |
|---|---|---|
| `GET /api/agents/status` | `agents` router has prefix `/agents` — no `/api` prefix, but frontend `apiGet("/agents/status")` adds `/api` automatically | Either add `/api` prefix to the agents router, or check if the main FastAPI app mounts it under `/api` via `APIRouter` |
| `GET /api/ai-feed` | `ai_feed` router requires `verify_api_key` (developer key), not JWT Bearer token | Frontend should use a dev API key header, or route needs auth relaxation |

**To investigate:** Run `curl http://localhost:8000/openapi.json | python3 -m json.tool | grep '"path"'` to see all real registered routes.

### 4.2 AI Insight Services Still Using Isolated HTTP Clients
`grok_insights.py` was fixed this session to use the shared `call_ai()` cascade. The other three services still have the same problem — isolated `httpx` clients with hardcoded models, no cascade fallback:

| File | Model Used | Issue |
|---|---|---|
| `app/services/claude_insights.py` | `claude-3-haiku-20240307` (old) | Isolated httpx; fails hard if Claude key invalid (no fallback) |
| `app/services/openai_insights.py` | `gpt-4o-mini` | Isolated httpx; no fallback; never tries newer models |
| `app/services/gemini_insights.py` | `gemini-2.0-flash` list | Has its own model fallback list, but still isolated (no cross-provider fallback) |

**Fix pattern** (same as what was done for `grok_insights.py`):
```python
from app.services.ai_client import call_ai

async def generate_match_insights(...) -> dict:
    raw = await call_ai(prompt, max_tokens=600, temperature=0.6, preferred="<provider>")
    if raw is None:
        return {**_no_key(), "error": "All AI providers unavailable"}
    # parse JSON from raw ...
```

These are called by `app/services/multi_ai_dispatcher.py` → match-detail AI insights panel.

### 4.3 Support Status Shows All Providers Unavailable
`GET /api/support/status` returns `{"providers": {"gemini": false, "claude": false, "openai": false, "grok": false}}` even though GEMINI and OPENAI keys are valid.

**Root cause:** `provider_status()` in `ai_client.py` calls `_provider_available()` which returns `false` if the provider is in the 30-minute backoff window (set when any prior call failed). Claude and Grok are invalid keys (3 chars) so they always backoff. Gemini/OpenAI may have hit an error on first attempt.

**Fix:** The status endpoint should distinguish between "key not configured", "in backoff", and "tested OK". The current implementation collapses these into a single boolean.

### 4.4 Gamification Tasks Not Seeded
The `tasks` and `task_categories` tables are empty. The Tasks page (`/tasks`) and the onboarding component (`components/onboarding.tsx`) will show nothing. There is task CRUD in the admin panel but no seed data.

**Fix:** Add a task seeding step to `main.py` startup (similar to how subscription plans and config defaults are seeded). Example categories: Prediction, Social, Training. Example tasks: "Make your first prediction", "Complete profile", "Refer a friend".

### 4.5 ML Performance Tracking Not Recording
`model_performances` = 0 rows. The `performance-monitor` agent runs every 30 minutes (with 90s initial delay) but has nothing to report because there are no settled predictions from the live API (football API is blocked) and match settlements have never triggered.

**Fix:** The agent should also process the synthetic settled predictions in the DB. Check `app/agents/performance_monitor.py` — it likely filters on `source != synthetic`.

---

## 5. Completed Work (this session + previous sessions)

### Session 1 — Prior fixes
- Puter.js multi-account panel (`ai-sources.tsx`, `puter-ai.ts`)
- `isPuterSignedIn`/`puterSignIn`/`puterSignOut`/`getPuterUser` exports
- DELAY_MS raised to 3500ms
- Rate-limit detection with 15s cooldown in agent loop
- JWT-based rate limiter keying with raised limits

### Session 2 — Top 10 bug fixes
1. Grok model names: `grok-2`/`grok-beta` → `grok-3-mini`/`grok-2-1212`
2. Provider 30-min backoff on 401/403 auth failures
3. Claude + Grok model loops `break` on auth failures
4. Match sync error logging uses `repr(e)` + exception type (was silent)
5. Misleading `pip install sports-skills` message replaced
6. Vite startup duplicate `--host --port` flags removed
7. Odds anomaly agent's private `_call_grok` → shared `call_ai` cascade
8. News sentinel logs when scraper returns empty
9. `ai_support.py` replaced Gemini-only `_call_gemini` with `call_ai` cascade
10. `/api/support/status` now reports per-provider availability

### Session 3 — Research tab + model upgrade
1. **EV Scanner status codes fixed** (`app/modules/quant/routes.py`): was filtering for `"SCHEDULED"/"TIMED"` (Football-Data.org codes) — added `"upcoming"`, `"scheduled"`, `"live"`, `"in_play"` so local DB statuses match
2. **`grok_insights.py` upgraded**: removed deprecated `grok-beta` + isolated `httpx` client; now uses shared `call_ai()` cascade with `preferred="grok"`, plus markdown fence stripping
3. **StrategyPanel empty-state fixed** (`frontend/src/pages/research.tsx`): missing `data?.error` handler left panel blank on no-data — added `<Err msg={data.error} />` guard (same pattern as other panels)
4. **Synthetic predictions seeded**: 15 predictions (9 settled, 6 open) seeded into `vit.db` with realistic probabilities, odds, and outcomes so all quant panels show real data

---

## 6. Priority Work Queue (next agent)

### P0 — Fix immediately (broken user-facing features)

**P0-A: Fix `/api/agents/status` 404**
- File: `app/api/routes/agents.py` (line 11: `prefix="/agents"`)
- File: `main.py` — check how this router is included (look for `include_router(agents_router...)`)
- The frontend calls `/api/agents/status` via `apiGet()` which prepends `/api`. Either add `/api` to the router prefix or wrap it.
- Also check: `GET /agents/providers` and `GET /agents/reports` — same prefix issue.

**P0-B: Add `RESEND_API_KEY` to enable email**
- `app/services/alerts.py` and email routes use Resend for transactional email
- Without this key, password reset, email verification, and notifications are broken
- Add the secret via Replit Secrets panel, not in code

**P0-C: Convert `claude_insights.py`, `openai_insights.py`, `gemini_insights.py` to use `call_ai` cascade**
- Follow exact same pattern as the fixed `grok_insights.py`
- These three files all have isolated `httpx` clients — no cross-provider fallback
- Priority: `claude_insights.py` first (Claude key is invalid, so all Claude insight calls fail hard)

### P1 — High value (significant UX improvement)

**P1-A: Seed gamification tasks**
- Add startup seeding in `main.py` for `task_categories` and `tasks` tables
- Minimum viable: 3 categories (Prediction, Social, Learning), 5-8 tasks each
- The Tasks page (`/tasks`) and `onboarding.tsx` component are complete — just need data

**P1-B: Fix provider status endpoint**
- `GET /api/support/status` always shows all providers as `false`
- Update `provider_status()` in `ai_client.py` to return three states: `"no_key"`, `"cooling"`, `"ok"`
- Update the status endpoint response to surface these three states
- This affects the AI Sources page and admin monitoring

**P1-C: Populate `model_performances` via performance monitor agent**
- `app/agents/performance_monitor.py` — check if it skips synthetic predictions
- Should record accuracy metrics against the 9 settled synthetic predictions
- This unblocks the Analytics page ROI chart, model contribution chart, and the Research terminal stats

**P1-D: Fix STRIPE_SECRET_KEY**
- Current value starts with `mk_1` — not a standard Stripe key prefix
  - `sk_live_…` = production
  - `sk_test_…` = test mode
  - `mk_1…` = unknown / possibly wrong format
- Subscription checkout will fail silently at payment intent creation
- Get a valid test key from Stripe dashboard and update the secret

### P2 — Medium priority (feature completeness)

**P2-A: Oracle node results pipeline**
- `oracle_results` = 0 despite `oracle-node` agent running every 600s
- Check `app/agents/oracle_node_agent.py` — likely requires live match settlements to produce output
- Could be made to run against synthetic completed matches
- Unblocks: Oracle page (`/oracle`), consensus_predictions table, validator scoring

**P2-B: CLV (Closing Line Value) tracking**
- `clv_entries` = 0
- `app/agents/audit_sentinel_agent.py` or `app/api/routes/admin_clv.py` should populate this
- CLV is a key analytics metric — needs to run against settled predictions
- The CLV tracking flag is set to `true` in health check but no entries are being written

**P2-C: Marketplace seed listings**
- `marketplace_listings` = 0 — the Marketplace page shows nothing
- Either add an admin UI to submit listings, or seed 2-3 example model listings at startup
- Model marketplace is a core monetization feature

**P2-D: Validator system bootstrap**
- `validator_profiles` = 0 — Validators page shows empty
- Add a startup seed that registers the admin user as a default validator
- The validator prediction system uses the oracle consensus layer

### P3 — Nice to have (polish & completeness)

**P3-A: Replace synthetic match data with real data alternative**
- Football-Data.org is blocked from Replit sandbox — consider switching to a free API that isn't blocked (e.g., `api-football.com` free tier, or `thesportsdb.com`)
- Alternatively: build a CSV/JSON fixture importer in admin panel so admins can upload real match schedules

**P3-B: Redis caching integration**
- `REDIS_URL` is configured but caching may be superficial
- Check `app/services/cache.py` or similar — identify which routes benefit from Redis
- High-value targets: predictions, match list, leaderboard, quant summary

**P3-C: ML model retraining pipeline**
- `training_jobs` = 0, `training_datasets` = 0
- `app/agents/retrain_trigger.py` runs every 12h but has no data to train on
- Needs at minimum 50+ settled predictions before retraining is meaningful
- Consider seeding more synthetic settled predictions (currently only 9)

**P3-D: Bridge & governance**
- `bridge_transactions` = 0, `gov_proposals` = 0
- These are complete features with working UIs but no data
- Low risk — pages degrade gracefully with empty states

---

## 7. File Quick-Reference

### Backend — Key files
| File | Purpose |
|---|---|
| `main.py` | App startup, router mounting, fixture seeding, agent boot |
| `app/db/models.py` | All SQLAlchemy ORM models |
| `app/db/database.py` | SQLite WAL config, `AsyncSessionLocal`, `get_db` |
| `app/config.py` | Module-level config vars (NOT a `settings` object) |
| `app/services/ai_client.py` | Shared AI cascade: Gemini→Claude→OpenAI→Grok, backoff logic |
| `app/services/grok_insights.py` | Match insights via `call_ai` cascade (fixed) |
| `app/services/claude_insights.py` | Match insights — **still isolated httpx** (needs P0-C fix) |
| `app/services/openai_insights.py` | Match insights — **still isolated httpx** (needs P0-C fix) |
| `app/services/gemini_insights.py` | Match insights — **still isolated httpx** (needs P0-C fix) |
| `app/services/multi_ai_dispatcher.py` | Fan-out match analysis to all 4 AI providers |
| `app/agents/coordinator.py` | Starts all 22 agents, `node_id` assignment |
| `app/agents/base.py` | `BaseAgent`: loop, interval, delay, error handling |
| `app/modules/quant/routes.py` | Research Terminal backend: backtest, monte-carlo, EV scanner, strategy |
| `app/api/routes/agents.py` | Agent status/trigger endpoints — **prefix issue** (see P0-A) |
| `app/api/routes/ai_support.py` | AI support chat endpoint with cascade |
| `app/api/routes/admin.py` | Full admin panel backend (large file) |
| `scripts/start_fullstack.sh` | Startup script (fixed duplicate Vite flags) |

### Frontend — Key files
| File | Purpose |
|---|---|
| `frontend/src/App.tsx` | Routes, lazy imports, auth wrappers |
| `frontend/src/lib/auth.tsx` | `useAuth()`, JWT storage, token refresh |
| `frontend/src/lib/apiClient.ts` | `apiGet`/`apiPost` — prepends `/api` to all paths |
| `frontend/src/lib/puter-ai.ts` | Puter.js browser AI (withRetry, sign-in/out) |
| `frontend/src/pages/research.tsx` | Research Terminal: backtester, Monte Carlo, EV scanner, strategy |
| `frontend/src/pages/agents.tsx` | Agent monitor — calls `/api/agents/status` (broken, see P0-A) |
| `frontend/src/pages/ai-sources.tsx` | AI provider panel + Puter multi-account |
| `frontend/src/pages/admin.tsx` | Full admin dashboard (large file) |

---

## 8. Coding Conventions

- **Database:** Always use `AsyncSession` from `app.db.database.get_db`. Never call `sqlite3` directly in app code (use aiosqlite for scripts only).
- **Config:** Read env vars via `os.getenv()` — no `settings` object. Config is in `app/config.py` as module-level variables.
- **AI calls:** Always use `call_ai()` from `app.services.ai_client` — never add new isolated httpx clients to provider APIs.
- **Auth:** All protected endpoints use `Depends(get_current_user)`. Admin endpoints additionally check `current_user.role == "admin"`.
- **Status codes:** Match status values in DB are **lowercase**: `upcoming`, `scheduled`, `live`, `in_play`, `completed`, `finished`. Never filter with uppercase Football-Data.org codes.
- **Error logging:** Use `repr(e)` and `type(e).__name__` in error logs — `str(e)` is often empty for network exceptions.
- **Frontend API calls:** `apiGet("/some/path")` prepends `/api` automatically → becomes `/api/some/path`.
- **Agent intervals:** All agents inherit from `BaseAgent`. To find an agent's run frequency, check its `interval` kwarg in `coordinator.py`.

---

## 9. Running the App

```bash
# Start everything (backend port 8000 + frontend port 5000)
bash scripts/start_fullstack.sh

# Health check
curl http://localhost:8000/health

# Get admin token (for API testing)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@vit.network","password":"<ADMIN_PASSWORD env var>"}'
```

The Replit workflow `Start application` runs `bash scripts/start_fullstack.sh` automatically.
