# VIT Sports Intelligence — Real Model Weights Training Plan

This guide takes the platform from synthetic-mode to real, production-grade
ensemble weights. It covers **what** to train, **where** to train it (Replit
vs. Colab vs. local), **when** to retrain, and **how** to wire the weights
back into the live orchestrator.

---

## 0. Current State (audit)

| Asset | Path | Status |
|---|---|---|
| Ensemble spec (12 models) | `services/ml_service/models/model_orchestrator.py` `_MODEL_SPECS` | ✅ Defined |
| Trainer for 5 sklearn models | `scripts/train_models.py` | ✅ Working |
| ETL / data generator | `scripts/generate_training_data.py` | ✅ Working |
| Calibration fitter | `scripts/fit_calibrators.py` | ✅ Working |
| Temperature scaler | `app/services/accuracy_enhancer.py` → `models/temperature.json` | ✅ Wired |
| Weight directory | `models/` | ✅ Exists, has `calibrators/` only |
| Feature flag | `USE_REAL_ML_MODELS=false` (`.replit`) | ⚠️ Off |
| Training data on disk | `vit.db.matches` | ❌ Only **100** settled rows — too small |

**The gap:** the trainer exists, but no `.pkl` files have been produced because
there isn't enough labeled data and the flag is off. Everything below addresses
that, end-to-end.

---

## 1. The 12 Models — what gets weights and what doesn't

From `_MODEL_SPECS`:

| # | Key | Type | Trainable? | Where |
|---|---|---|---|---|
| 1 | `logistic_v1` | sklearn LogisticRegression | ✅ pickle | scripts/train_models.py |
| 2 | `rf_v1` | sklearn RandomForest | ✅ pickle | scripts/train_models.py |
| 3 | `xgb_v1` | XGBoost | ✅ pickle | scripts/train_models.py |
| 4 | `gbm_v1` | sklearn GradientBoosting | ✅ pickle | scripts/train_models.py |
| 5 | `lgbm_v1` | LightGBM | ✅ pickle | scripts/train_models.py |
| 6 | `poisson_v1` | Closed-form Poisson | 🟡 fit λ priors | new: scripts/train_poisson.py |
| 7 | `dixon_coles_v1` | Dixon–Coles MLE | 🟡 fit ρ, attack/defense | new: scripts/train_dixon_coles.py |
| 8 | `elo_v1` | Elo replay | 🟡 fit K-factor + initial ratings | new: scripts/train_elo.py |
| 9 | `bayes_v1` | Bayesian net | 🟡 fit conjugate priors per league | new: scripts/train_bayes.py |
| 10 | `lstm_v1` | LSTM (sequence) | ⚠️ GPU recommended | Colab/Kaggle |
| 11 | `transformer_v1` | Transformer-light | ⚠️ GPU recommended | Colab/Kaggle |
| 12 | `ensemble_v1` / `hybrid_v1` / `market_v1` | Stacked meta + heuristic | ✅ fit stacker on OOF preds | scripts/train_stack.py |

> `market_v1` is a pure market-implied baseline — no weights needed; it just
> needs odds at predict time. Keep it as the benchmark.

---

## 2. Data — the foundation

You cannot get past ~52% accuracy without real, broad, labeled history. The
target dataset is **5–8 seasons × top-5 European leagues + 3 secondary leagues**,
i.e. roughly **9,000–15,000 settled matches** with closing odds.

### 2.1 Sources

| Source | Cost | Quality | Use for |
|---|---|---|---|
| **football-data.co.uk** | Free | Excellent (back to 1993, with B365/PS/WH odds) | **Primary backfill** |
| **OpenFootball / engelsi** | Free | Good (no odds) | Cross-validation of fixtures |
| **OddsPortal scraper** | Free (TOS-grey) | Excellent for closing lines | Avoid; legal risk |
| **The Odds API** | $0–$30/mo | Fresh closing lines | Live odds only |
| **football-data.org API** | Free tier | Fixtures + scores, no odds | Future fixtures |
| **API-FOOTBALL (RapidAPI)** | $19/mo Pro | Stats + lineups + xG | Feature enrichment |

**Recommended free path:** download CSVs from football-data.co.uk for each
league/season, concat them, and feed `scripts/train_models.py --source csv`.

### 2.2 Backfill steps

1. From a shell:
   ```bash
   mkdir -p data/raw
   cd data/raw
   for season in 1819 1920 2021 2122 2223 2324 2425; do
     for league in E0 E1 SP1 D1 I1 F1 N1 P1; do
       curl -sSO "https://www.football-data.co.uk/mmz4281/${season}/${league}.csv"
     done
   done
   ```
2. Concatenate:
   ```bash
   python -c "
   import pandas as pd, glob
   df = pd.concat([pd.read_csv(f, encoding='latin-1') for f in glob.glob('data/raw/*.csv')], ignore_index=True)
   df.to_csv('data/historical_matches.csv', index=False)
   print(len(df), 'rows')"
   ```
3. Sanity check column names (`HomeTeam`, `AwayTeam`, `FTHG`, `FTAG`, `FTR`,
   `B365H`, `B365D`, `B365A` are the common ones — `train_models.py`'s feature
   extractor already understands these aliases).

### 2.3 Loading into the database (so future routes can use it)

```bash
python scripts/generate_training_data.py --csv data/historical_matches.csv --commit
```

This writes to `matches` with `actual_outcome` populated. Verify:
```bash
sqlite3 vit.db "SELECT league, COUNT(*) FROM matches WHERE actual_outcome IS NOT NULL GROUP BY league"
```
Goal: **≥ 1,500 matches per league** for the top-5; 500+ for secondary.

---

## 3. Training — three execution environments

### Tier A — **Replit (CPU, ≤2GB models)**
**Use for:** logistic, RF, GBM, XGBoost, LightGBM, Poisson, Dixon–Coles, Elo,
Bayes, stacker.
**Wall-clock:** 5–15 min for the whole sklearn batch on 10k rows.

```bash
# 1. Make sure data is loaded (above).
# 2. Train the sklearn ensemble:
python scripts/train_models.py --source both --csv data/historical_matches.csv

# 3. Fit calibrators (per-model isotonic + global temperature scaling):
python scripts/fit_calibrators.py

# 4. Verify outputs:
ls -la models/
#   logistic_v1.pkl, rf_v1.pkl, xgb_v1.pkl, gbm_v1.pkl, lgbm_v1.pkl,
#   temperature.json, calibrators/*.pkl
```

### Tier B — **Google Colab (free GPU)**
**Use for:** `lstm_v1`, `transformer_v1`. 10k matches × sequence length 10
trains in ~20 min on a T4.

Suggested notebook structure (`notebooks/train_sequence_models.ipynb`):
1. Mount Drive, upload `data/historical_matches.csv`.
2. Build per-team sequences: last-N matches → next-match outcome.
3. Train LSTM (PyTorch or Keras) — small, ~50k params is plenty.
4. Train tiny Transformer (4 heads, 2 layers, 64-d).
5. Export with `joblib.dump({"model": state_dict, "config": {...}, ...},
   "lstm_v1.pkl")` using the **same payload schema** as
   `scripts/train_models.py` (`model`, `scaler`, `feature_columns`,
   `class_labels`, `metrics`, `version`).
6. Download both `.pkl` files, drop them into `models/`.

> Schema match matters — the orchestrator's `model_loader` (in
> `services/ml_service/model_loader.py`) reads `feature_columns` and `scaler`
> by name. Diverging keys = silent fallback to synthetic.

### Tier C — **Kaggle / local box (only for full retrain)**
**Use for:** quarterly full retrain on 5+ seasons with hyperparameter search
(Optuna over XGB / LGBM). Kaggle gives 30 GPU hrs/week free, plenty.

---

## 4. Stacking & meta-models

After Tier A + B finish, fit `ensemble_v1` and `hybrid_v1`:

1. Generate **out-of-fold predictions** for each base model using a 5-fold
   chronological split (no leakage from future to past).
2. Train a small meta-learner (LogisticRegression with L2 or shallow
   GradientBoosting) on the matrix of OOF probabilities → outcome.
3. Save as `ensemble_v1.pkl` / `hybrid_v1.pkl`.

Add a script `scripts/train_stack.py` mirroring the schema of
`scripts/train_models.py`. Acceptance: stacker accuracy ≥ best single base
model + 0.5 pp.

---

## 5. Calibration & evaluation

Already wired:
- `scripts/fit_calibrators.py` → per-model isotonic regression
- `app/services/accuracy_enhancer.py::TemperatureScaler` → global temperature

Add to your post-training checklist:
| Metric | Target | Where measured |
|---|---|---|
| Multi-class log-loss | ≤ 1.00 | `scripts/train_models.py` prints it |
| Brier score (1×2) | ≤ 0.59 | add to `scripts/analyze_predictions.py` |
| Calibration ECE | ≤ 0.04 | `scripts/fit_calibrators.py` |
| ROI on flat $1 stakes vs. Pinnacle close | ≥ –1% (beats market) | `scripts/bankroll_backtest.py` |

If ROI is worse than –3%, **do not promote the weights** — the model is
worse than betting blind.

---

## 6. Wiring weights into production

Once `models/*.pkl` exist:

1. Flip the flag — in Replit Secrets / `.replit`:
   ```
   USE_REAL_ML_MODELS=true
   ```
2. Restart the workflow:
   ```bash
   # via the Workflows panel, or:
   pkill -f "python main.py"
   ```
3. On boot, look for this log line:
   ```
   ✅ Orchestrator initialized: 12 models   (pkl_loaded=10/12)
   ```
   `pkl_loaded` should equal the number of `.pkl` files in `models/`.
4. Hit `GET /api/ai/models/status` — every entry should show `pkl_loaded:
   true` with a non-zero `accuracy` from the stored metrics.
5. Run a smoke prediction:
   ```bash
   curl -s "$REPLIT_DEV_DOMAIN/api/predictions/<match_id>" | jq '.predictions'
   ```
   `pkl_models_active` in the response confirms it.

---

## 7. Retraining cadence

| Trigger | Job | Owner |
|---|---|---|
| Every Monday 03:00 UTC | Refresh weekend results, append to DB | cron / Replit Scheduled Deployment |
| Weekly | Re-fit calibrators only (cheap, 2 min) | scheduled |
| Monthly | Re-fit sklearn batch (Tier A) | scheduled |
| Quarterly | Full retrain incl. sequence models (Tier B) | manual / notebook |
| On accuracy drop | Auto-trigger if rolling 30-day Brier > 0.62 | `app/modules/ai/weight_adjuster.py` already has hooks — extend it |

Add a cron-style scheduled deployment (Replit → Scheduled Deployment) that
runs `python scripts/train_models.py --source db` weekly. It will pick up new
settled matches automatically.

---

## 8. Storage & versioning

- `models/` is gitignored by default — that's correct, weights are large.
- Version every `.pkl` with the `"version"` key in the payload (already done).
- For traceability, also log the training event to the `ModelMetadata` table
  via `app/modules/ai/registry.py::register_model()` — pass `accuracy`,
  `log_loss`, `training_samples`. The admin Models page reads from there.
- Backups: copy `models/*.pkl` to a private object store after each successful
  Tier A/B run. Replit Object Storage works.

---

## 9. Risk & guardrails

1. **No silent fallback to synthetic.** Already enforced in
   `app/modules/ai/orchestrator.py` lines 56–61 — if any 1×2 prob is missing,
   it raises. Keep it that way.
2. **Stake limits** stay in place even with real models — `MAX_STAKE` env var
   and `MIN_EDGE_THRESHOLD` already gate publication.
3. **A/B before promote.** When introducing a new `_v2` weight set, register it
   alongside `_v1` in `_MODEL_SPECS`, give it 0 base weight, accumulate 30+
   days of shadow predictions, then graduate via `weight_adjuster`.

---

## 10. Suggested execution order (this week)

1. **Day 1** — backfill data (Section 2.1–2.3). Outcome: `matches` table has
   ≥ 8,000 settled rows.
2. **Day 1** — `python scripts/train_models.py --source db`. Outcome: 5
   `.pkl` files in `models/`.
3. **Day 1** — `python scripts/fit_calibrators.py`. Outcome: calibrators +
   `temperature.json`.
4. **Day 2** — write/run `scripts/train_poisson.py`,
   `scripts/train_dixon_coles.py`, `scripts/train_elo.py`,
   `scripts/train_bayes.py`. Outcome: 4 more `.pkl` files.
5. **Day 3** — write `scripts/train_stack.py`, fit `ensemble_v1` +
   `hybrid_v1`. Outcome: 2 more `.pkl` files.
6. **Day 4** — open Colab notebook for `lstm_v1` + `transformer_v1`. Outcome:
   2 more `.pkl` files (12 total — full ensemble).
7. **Day 5** — flip `USE_REAL_ML_MODELS=true`, restart, run backtest, verify
   ROI ≥ –1% vs. closing lines. Promote to production.
8. **Day 6** — set up the Monday cron retrain.

---

**Definition of done:** `GET /api/ai/models/status` reports
`{"ready": 12, "total": 12}` with every model showing real `accuracy` and
`log_loss` from the trained payload, and `/api/predictions/<id>` returns
`pkl_models_active >= 10`.
