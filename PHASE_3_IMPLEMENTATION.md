# Phase 3: Next-Phase Implementation Plan
**Status:** 📋 Ready to build  
**Current Version:** 4.7.5  
**Target:** Complete P3 features + resolve remaining P2 gaps  
**Estimated effort:** 3-4 development sessions (4-6 hours each)

---

## 📊 Phase Breakdown

### **Phase 3a: Data & Integration (Session 1-2)**
Priority: **CRITICAL** — unblock real ML pipeline

#### **P3a-1: Replace Synthetic Matches with Real Data** ⭐ HIGH IMPACT
**Why:** Football-Data.org is Replit-blocked (TCP timeout); system runs fully synthetic  
**Impact:** Real match data → ML training pipeline can work → performance monitor generates real metrics

**Options:**
1. **TheSportsDB API** (free, no auth) ✅ RECOMMENDED
   - No rate limits, no authentication
   - Covers 100+ leagues, 20+ years history
   - Slow but reliable (2-3s per league)
   - Code: `app/services/sportsdb_api.py` already exists

2. **api-football.com** (free tier)
   - 100 req/day limit (sufficient for dev)
   - Requires API key
   - Faster than TheSportsDB

3. **CSV Import UI** (backup)
   - Admin panel upload for `.csv` fixture files
   - Local control over data

**Implementation:**
```python
# app/services/sportsdb_api.py (already started — extend it)

async def fetch_all_real_fixtures(days_back: int = 365) -> dict:
    """Fetch real fixtures from TheSportsDB for all major leagues."""
    
async def sync_fixture_results(db: AsyncSession) -> dict:
    """Poll for match results and update Match.actual_outcome."""
    
async def backfill_historical_matches(db: AsyncSession, months: int = 24) -> int:
    """Pre-populate DB with past seasons' results for ML training."""
```

**Subtasks:**
- [ ] Complete `fetch_all_real_fixtures()` → parse response + insert Match rows
- [ ] Add `sync_fixture_results()` → call every 4h, update outcomes
- [ ] Backfill 500+ historical matches (2 seasons)
- [ ] Update startup sequence in `main.py` to call backfill
- [ ] Add admin endpoint `/admin/fixtures/sync` to trigger manually

**Acceptance:**
- `matches` table has 500+ rows with `source='sportsdb'`
- `Match.actual_outcome` populated for completed matches
- Performance monitor agent generates real metrics

---

#### **P3a-2: Extend Synthetic Predictions Seed (9 → 50)** ⭐ MEDIUM
**Why:** Only 9 settled predictions; ML retraining needs 50+  
**Impact:** More training data → model accuracy shows real variance

**Implementation:**
```python
# scripts/seed_extended_predictions.py

async def seed_predictions(db: AsyncSession, count: int = 50) -> dict:
    """
    For each real match from TheSportsDB:
    - Generate 3-5 predictions from different "model sources"
    - Assign realistic odds from 1.5-3.5 range
    - For past matches: set actual_outcome + was_correct randomly (60% win rate)
    """
```

**Subtasks:**
- [ ] Create `scripts/seed_extended_predictions.py`
- [ ] For each Match with actual_outcome, generate 3 Prediction rows
- [ ] Seed CLVEntry rows (opening_odds, closing_odds, bet_outcome)
- [ ] Call from startup or `/admin/fixtures/backfill` endpoint

**Acceptance:**
- `predictions` table has 150+ rows (3x more)
- 90+ are settled (with `was_correct` set)
- All CLV data populated

---

### **Phase 3b: ML Pipeline & Monitoring (Session 2-3)**
Priority: **HIGH** — enable autonomous learning system

#### **P3b-1: Retraining Pipeline Bootstrap** ⭐ CORE FEATURE
**Why:** `training_jobs=0`; retrain agent runs but has nothing to do  
**Impact:** Models auto-train on new settled data every 12h

**Implementation:**
```python
# app/agents/retrain_trigger.py (already exists — enhance it)

async def run_cycle(self) -> dict:
    """
    1. Count settled predictions in last 24h
    2. If >= 50: create TrainingJob for top 3 underperforming models
    3. Call app/services/model_training.py:train_model_async()
    4. On success: update ModelMetadata.active_version + weights
    """
```

**Subtasks:**
- [ ] Create `app/services/model_training.py` with `train_model_async(model_key, db)`
- [ ] Enhance `retrain_trigger.py` to check settled count + create jobs
- [ ] Add job progress tracking (events, progress_pct, current_model)
- [ ] Backend endpoint: `POST /api/admin/training/retrain/{model_key}` (manual trigger)
- [ ] Frontend: Admin dashboard widget showing training queue + progress

**Acceptance:**
- `training_jobs` table populated (auto-created when conditions met)
- Jobs show `status=running` → `status=completed`
- ModelMetadata weights updated post-training

---

#### **P3b-2: Model Performance Dashboard** ⭐ UX FEATURE
**Why:** No visibility into model accuracy trends  
**Impact:** Users see which models are winning/losing

**Implementation:**
```typescript
// frontend/src/pages/model-performance.tsx

- Line charts: accuracy over time (30d rolling)
- Heatmap: model vs league (6x12 grid)
- Leaderboard: ranking by Sharpe ratio / ROI
- Alerts: "Model X has 3-day losing streak"
```

**Subtasks:**
- [ ] Backend endpoint: `GET /api/models/performance?days=30`
- [ ] Return: `[{model_key, samples, accuracy, sharpe, roi, streak_days, trend}]`
- [ ] Frontend React component (recharts)
- [ ] Add to dashboard sidebar

**Acceptance:**
- Dashboard displays live model stats
- Performance monitor agent populates `model_performances` table
- Charts update every 30 min

---

### **Phase 3c: User Features (Session 3-4)**
Priority: **MEDIUM** — improve user experience

#### **P3c-1: Bankroll Management System** ⭐ WALLET FEATURE
**Why:** `bankroll_states=0`; users can't track profit/loss  
**Impact:** Users see Kelly criterion recommendations, risk metrics

**Implementation:**
```python
# app/modules/bankroll/routes.py (new)

GET  /api/bankroll/state        → current balance, ROI, Kelly %, max_loss_limit
GET  /api/bankroll/history      → 30d profit/loss chart
POST /api/bankroll/set-limit    → set max daily loss

# Backend calculation
kelly_percent = (win_rate * odds - 1) / (odds - 1)
suggested_stake = bankroll * kelly_percent * 0.25  # quarter Kelly
```

**Subtasks:**
- [ ] Create `app/modules/bankroll/models.py` + `BankrollState`
- [ ] Create routes with Kelly calculation
- [ ] Frontend component: `/pages/bankroll.tsx`
- [ ] Chart: 30d rolling P&L with Kelly lines
- [ ] Auto-suggest bet size based on Kelly

**Acceptance:**
- Bankroll page shows Kelly %, max loss limit, 30d P&L
- Predictions show "Suggested: 2.3% bankroll" label

---

#### **P3c-2: Notification System Completion** ⭐ PUSH FEATURE
**Why:** `notifications=0`; RESEND_API_KEY missing  
**Impact:** Users get alerts for prediction results, model status

**Implementation:**
```python
# app/modules/notifications/service.py (enhance)

async def send_prediction_result(prediction_id: int, outcome: str):
    """Notify user when their prediction settles (win/loss/void)."""
    
async def send_model_alert(model_key: str, event: str):
    """Notify admin when model demotion/failure detected."""
```

**Subtasks:**
- [ ] Add RESEND_API_KEY to Replit Secrets (ACTION REQUIRED)
- [ ] Create email templates (result, alert, verification)
- [ ] Frontend: Notification preferences page
- [ ] Backend: `POST /api/notifications/preferences`
- [ ] Telegram integration already working

**Acceptance:**
- Email sent on prediction result
- Admin gets Telegram alert on model failure
- Users can opt in/out per channel

---

### **Phase 3d: Polish & Completeness (Session 4)**
Priority: **LOW** — nice-to-have improvements

#### **P3d-1: Governance MVP** ⭐ DAO FEATURE
**Why:** `gov_proposals=0`; DAO structure exists but unused  
**Impact:** Users can vote on platform decisions (fee changes, new leagues, etc.)

**Implementation:**
```python
# app/modules/governance/routes.py (enhance with proposals)

POST   /api/governance/proposals        → create proposal
GET    /api/governance/proposals        → list active
POST   /api/governance/proposals/{id}/vote  → cast vote
POST   /api/governance/proposals/{id}/execute → execute if passed
```

**Subtasks:**
- [ ] Create proposal types (FEE_CHANGE, ADD_LEAGUE, MODEL_DEPRECATION, etc.)
- [ ] Voting logic: 1 VIT token = 1 vote
- [ ] Frontend: proposal creation + voting UI
- [ ] Auto-execute approved proposals (e.g., update fee_rates config)

**Acceptance:**
- Admin can create governance proposal
- Users vote (weighted by VIT balance)
- Proposal auto-executes on passage

---

#### **P3d-2: Bridge & Cross-Chain Polish**
**Why:** `bridge_transactions=0`; bridge exists but not demonstrated  
**Impact:** Users see working token bridge (even if testnet)

**Subtasks:**
- [ ] Add bridge pool seeding (VIT↔USDT, VIT↔ETH)
- [ ] Create test transaction flow in admin panel
- [ ] Document bridge security model
- [ ] Add `/pages/bridge.tsx` with live pool status

**Acceptance:**
- Bridge page shows 3 active pools
- Test bridge transaction succeeds (testnet)
- Pool stats (liquidity, volume) displayed

---

## 🛠️ Implementation Priority

### **Must-Have (Unblocks downstream features)**
1. ✅ P3a-1: Real match data (TheSportsDB)
2. ✅ P3a-2: Extended predictions seed
3. ✅ P3b-1: Retraining pipeline
4. ✅ P3b-2: Performance dashboard

### **Should-Have (Significant UX impact)**
5. ✅ P3c-1: Bankroll management
6. ✅ P3c-2: Notification completion (needs RESEND_API_KEY)

### **Nice-to-Have (Polish)**
7. P3d-1: Governance MVP
8. P3d-2: Bridge polish

---

## 📋 Session-by-Session Breakdown

### **Session 1: Data Integration & ML Foundation (4-5 hours)**
**Goal:** Real data in, ML pipeline operational

**Deliverables:**
- [ ] TheSportsDB integration: 500+ historical matches
- [ ] Extended predictions seed: 150+ predictions (90+ settled)
- [ ] CLV data backfill
- [ ] Startup integration

**Testing:**
```bash
# Verify data loaded
sqlite3 vit.db "SELECT COUNT(*) FROM matches WHERE source='sportsdb';"  # Should be 500+
sqlite3 vit.db "SELECT COUNT(*) FROM predictions WHERE was_correct IS NOT NULL;"  # Should be 90+
sqlite3 vit.db "SELECT COUNT(*) FROM clv_entries;"  # Should be 150+

# Check performance monitor
curl http://localhost:8000/api/models/performance
```

---

### **Session 2: ML Training & Monitoring (4-5 hours)**
**Goal:** Models auto-train, performance visible

**Deliverables:**
- [ ] Retraining pipeline: jobs auto-created
- [ ] Model performance dashboard: accuracy trends
- [ ] Training job UI: progress tracking
- [ ] Manual trigger endpoint

**Testing:**
```bash
# Trigger retrain manually
curl -X POST http://localhost:8000/api/admin/training/retrain/xgboost_v1 \
  -H "Authorization: Bearer <token>"

# Check training job status
curl http://localhost:8000/api/admin/training/jobs

# View performance metrics
curl http://localhost:8000/api/models/performance?days=30
```

---

### **Session 3: User Features & Notifications (3-4 hours)**
**Goal:** Users see bankroll, get notified, engage with platform

**Deliverables:**
- [ ] Bankroll management system
- [ ] Kelly criterion calculations
- [ ] Notification preferences UI
- [ ] Email template setup (requires RESEND_API_KEY)

**Testing:**
```bash
# Set bankroll limit
curl -X POST http://localhost:8000/api/bankroll/set-limit \
  -d '{"max_daily_loss": 50}' \
  -H "Authorization: Bearer <token>"

# Get bankroll state
curl http://localhost:8000/api/bankroll/state \
  -H "Authorization: Bearer <token>"
```

---

### **Session 4: Polish & Completeness (2-3 hours)**
**Goal:** DAO governance visible, bridge polished

**Deliverables:**
- [ ] Governance proposal system
- [ ] Bridge pool seeding + demo flow
- [ ] Frontend components for both

---

## 🚀 Quick-Start Commands

### **Full Phase 3 Build**
```bash
# 1. Pull latest code
git pull origin main

# 2. Start fresh DB
rm vit.db
bash scripts/start_fullstack.sh

# 3. Backend should seed:
#    - 500+ real matches
#    - 150+ predictions (90+ settled)
#    - CLV entries
#    - Task categories (from Phase 2)

# 4. Verify health
curl http://localhost:8000/health

# 5. Check data
curl http://localhost:8000/api/models/performance
curl http://localhost:8000/api/support/status
```

---

## 📝 Acceptance Criteria

### **Phase 3 Complete When:**
- ✅ `matches` table has 500+ rows (source='sportsdb')
- ✅ `predictions` table has 150+ rows with 90+ settled
- ✅ `training_jobs` auto-created and completed
- ✅ Performance dashboard shows live accuracy trends
- ✅ Bankroll page shows Kelly calculations
- ✅ Notifications sent on prediction results
- ✅ `/api/health` returns `models_loaded: 12, db_connected: true, accuracy: 58.5%`
- ✅ Frontend agents page loads without 404
- ✅ All tests pass: `pytest tests/ -v`

---

## 🔗 Dependencies & Blockers

### **Blocking Phase 3:**
- ❌ RESEND_API_KEY (required for email notifications)
  - **Workaround:** Comment out email sends in P3c-2
- ❌ STRIPE_SECRET_KEY (has wrong format)
  - **Workaround:** Low priority — subscriptions can wait

### **Not Blocking:**
- ✅ Football-Data.org (using TheSportsDB instead)
- ✅ Real ML models (synthetic data is sufficient)

---

## 📚 Related Files

### **New Files to Create**
- `app/services/sportsdb_api.py` (extend)
- `app/services/model_training.py` (new)
- `scripts/seed_extended_predictions.py` (new)
- `app/modules/bankroll/routes.py` (new)
- `app/modules/bankroll/models.py` (new)
- `frontend/src/pages/model-performance.tsx` (new)
- `frontend/src/pages/bankroll.tsx` (new)

### **Files to Modify**
- `main.py` (add startup calls for TheSportsDB sync)
- `app/agents/retrain_trigger.py` (enhance logic)
- `app/config.py` (add SPORTSDB constants)
- `frontend/src/App.tsx` (add new routes)

---

**Ready to build? Start with Session 1 (Data Integration). Good luck! 🚀**
