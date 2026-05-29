# JULES TASK INSTRUCTIONS — VIT_OS UPGRADE
> ⚠️ CRITICAL: This is an UPGRADE to an existing system. Do NOT delete or overwrite existing files unless explicitly instructed. Extend, refactor, and integrate only.

---

## SYSTEM CONTEXT: EXISTING VIT_OS
The existing VIT_OS system already has:
- **CSV training data pipeline** covering EPL, La Liga, Bundesliga, Serie A, Ligue 1, Champions League (2020–2024)
- **Trained `.pkl` models** (Scikit-learn / XGBoost based) for match outcome prediction
- **B365 odds columns** integrated as features
- **Deployment on Replit** (active)
- **Basic prediction endpoint** serving results

Your job is to **upgrade this into a fully self-contained VIT AI** that replaces all external AI API dependencies (Google Gemini, DeepSeek, OpenAI, etc.) with internally owned VIT components — without breaking the existing prediction pipeline.

---

## UPGRADE OBJECTIVES (DO ALL IN PARALLEL)

### 🔴 PRIORITY 1 — Audit Existing Codebase
Before writing any new code:
1. Scan all `.py` files for any `import openai`, `import google.generativeai`, `import deepseek`, `requests` calls to external LLM APIs, or any hardcoded API keys.
2. Generate a file called `AUDIT_REPORT.md` listing:
   - Every file that calls an external AI service
   - What it's being used for (reasoning, summarization, embedding, etc.)
   - Which VIT module will replace it
3. Do NOT modify any audited files yet — audit first, then proceed.

---

### 🟠 MODULE 1 — VIT Brain (Local LLM: Replace External AI Calls)
**Goal:** Replace all external LLM API calls with a locally served Ollama / GGUF model.

**Tasks:**
1. Create `vit_brain/` directory (if not exists).
2. Create `vit_brain/vit_brain_client.py`:
   - Class `VITBrain` with method `ask(prompt: str) -> str`
   - Internally calls local Ollama endpoint: `http://localhost:11434/api/generate`
   - Model: `mistral` or `llama3` (configurable via `config.yaml`)
   - Falls back gracefully with a clear error if Ollama is not running
   - Add `async` support using `httpx`
3. Create `vit_brain/prompts/`:
   - `match_analysis.txt` — prompt template for pre-match reasoning
   - `odds_analysis.txt` — prompt template for identifying value bets
   - `injury_impact.txt` — prompt template for assessing squad news impact
4. Create `vit_brain/vit_brain_trainer_colab.ipynb`:
   - Google Colab notebook using **Unsloth + LoRA** to fine-tune `Mistral 7B`
   - Training data: football instruction-response pairs (Jules should generate 50 example pairs covering match previews, xG interpretation, odds value, lineup changes)
   - Save output as `vit_brain_lora_adapter/` (Hugging Face format)
   - Include instructions to push weights to Hugging Face Hub free tier
5. Update `config.yaml` to add `vit_brain` section:
   ```yaml
   vit_brain:
     model: mistral
     endpoint: http://localhost:11434/api/generate
     temperature: 0.3
     max_tokens: 512
   ```

---

### 🟡 MODULE 2 — VIT Memory (Local RAG: Replace External Embeddings/Search)
**Goal:** Build a fully local RAG pipeline using ChromaDB + sentence-transformers. No Pinecone, no external embedding APIs.

**Tasks:**
1. Create `vit_memory/` directory (if not exists).
2. Create `vit_memory/vit_memory_store.py`:
   - Class `VITMemory`
   - Uses `chromadb` (local persistent storage at `./vit_memory/chroma_store/`)
   - Uses `sentence-transformers` model `all-MiniLM-L6-v2` for local embeddings
   - Methods:
     - `ingest_match(match_dict: dict)` — embed and store a match record
     - `ingest_text(text: str, metadata: dict)` — embed and store free text (injury news, press conf)
     - `query(question: str, n_results: int = 5) -> list` — semantic search
     - `ingest_csv(filepath: str)` — bulk ingest existing CSV training data into vector store
3. Create `vit_memory/vit_memory_pipeline.py`:
   - Automatically ingests all CSVs from `vit_data/` directory on startup
   - Watches `vit_data/` for new CSVs and ingests incrementally
4. Create `vit_memory/retriever.py`:
   - `VITRetriever` class combining ChromaDB query results with VITBrain prompts
   - Method: `retrieve_and_reason(question: str) -> str`
   - Fetches top-5 relevant match records → injects into VITBrain prompt → returns answer
5. ⚠️ Do NOT delete existing CSV files or SQLite databases.

---

### 🟢 MODULE 3 — VIT Nerve (FastAPI Orchestrator: Unified Endpoint)
**Goal:** Replace any scattered external API calls with a single internal FastAPI router that orchestrates VITBrain + VITMemory + existing `.pkl` prediction models.

**Tasks:**
1. If `main.py` or `app.py` already exists — **extend it**, do not replace it.
2. Create or extend `vit_nerve/router.py` with these endpoints:
   - `POST /vit/predict` — runs existing `.pkl` model prediction (keep existing logic)
   - `POST /vit/ask` — routes query through VITBrain (local LLM)
   - `POST /vit/search` — queries VITMemory RAG store
   - `POST /vit/analyze` — full pipeline: RAG retrieval → VITBrain reasoning → prediction score
   - `GET /vit/health` — returns status of all VIT components (Brain online, Memory loaded, Engine ready)
3. Create `vit_nerve/schemas.py` — Pydantic models for all request/response bodies.
4. Create `vit_nerve/orchestrator.py`:
   - `VITOrchestrator` class that initializes Brain, Memory, and Engine together
   - Singleton pattern — load once on startup, reuse across requests
   - CPU-optimized — all model loading uses `torch.set_num_threads(4)` and float32
5. Update `render.yaml` (or create if missing):
   ```yaml
   services:
     - type: web
       name: vit-nerve-api
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: uvicorn main:app --host 0.0.0.0 --port 10000
     - type: worker
       name: vit-scraper
       env: python
       startCommand: python vit_scraper/scrape_and_update.py
   ```

---

### 🔵 MODULE 4 — VIT Scraper (Upgrade Existing Scrapers)
**Goal:** Upgrade any existing scrapers to feed data into VITMemory automatically.

**Tasks:**
1. Locate existing scraper files. If found, extend them. If none found, create `vit_scraper/scrape_and_update.py`.
2. Add scrapers for:
   - **FBref** — xG, match stats per league
   - **football-data.org** — fixtures, results (free API key via env var `FOOTBALL_DATA_API_KEY`)
   - **Transfermarkt** — squad depth, player values (Playwright headless)
3. After each scrape cycle:
   - Save new data as CSV to `vit_data/raw/`
   - Auto-ingest into VITMemory via `VITMemory.ingest_csv()`
4. Schedule scrape every 6 hours using `APScheduler`.
5. Log all scrape results to `vit_data/logs/scrape_log.txt`.

---

### ⚪ MODULE 5 — VIT Engine (Upgrade Existing .pkl Models)
**Goal:** Keep existing `.pkl` models intact. Add parallel PyTorch LSTM model for form tracking.

**Tasks:**
1. Do NOT remove or modify existing `.pkl` prediction pipeline.
2. Create `vit_engine/lstm_form_model.py`:
   - PyTorch LSTM model taking last-5-match rolling features as input
   - Input: `[home_xg, away_xg, home_goals, away_goals, odds_movement]` × 5 timesteps
   - Output: win probability vector `[home_win, draw, away_win]`
   - Save trained weights as `vit_engine/vit_lstm.pt`
3. Create `vit_engine/vit_engine_colab.ipynb`:
   - Google Colab notebook to train LSTM on existing CSV data
   - Uses PyTorch, saves `.pt` file for Render CPU inference
4. Create `vit_engine/ensemble.py`:
   - `VITEnsemble` class combining `.pkl` model output + LSTM output
   - Weighted blend: 60% pkl model, 40% LSTM (configurable in `config.yaml`)
   - Method: `predict(features: dict) -> dict` returns final probabilities + confidence score

---

## DEPENDENCY FILE
Create/update `requirements.txt` with all required packages:
```
fastapi
uvicorn
pydantic
torch
scikit-learn
xgboost
lightgbm
pandas
numpy
chromadb
sentence-transformers
langchain
langchain-community
httpx
playwright
beautifulsoup4
apscheduler
duckdb
mlflow
optuna
peft
transformers
unsloth
bitsandbytes
PyYAML
python-dotenv
```

---

## ENVIRONMENT VARIABLES
Create `.env.example` (never commit `.env`):
```
FOOTBALL_DATA_API_KEY=your_key_here
RAPIDAPI_KEY=your_key_here
HF_TOKEN=your_huggingface_token
VIT_BRAIN_ENDPOINT=http://localhost:11434/api/generate
VIT_BRAIN_MODEL=mistral
```

---

## REPO STRUCTURE TARGET
After Jules completes all tasks, the repo should look like:
```
vit_os/
├── vit_brain/
│   ├── vit_brain_client.py
│   ├── vit_brain_trainer_colab.ipynb
│   └── prompts/
│       ├── match_analysis.txt
│       ├── odds_analysis.txt
│       └── injury_impact.txt
├── vit_memory/
│   ├── vit_memory_store.py
│   ├── vit_memory_pipeline.py
│   └── retriever.py
├── vit_nerve/
│   ├── router.py
│   ├── schemas.py
│   └── orchestrator.py
├── vit_engine/
│   ├── lstm_form_model.py
│   ├── vit_engine_colab.ipynb
│   └── ensemble.py
├── vit_scraper/
│   └── scrape_and_update.py
├── vit_data/
│   ├── raw/
│   └── logs/
├── config.yaml
├── requirements.txt
├── render.yaml
├── .env.example
├── AUDIT_REPORT.md   ← Jules generates this first
└── main.py           ← existing file, extended not replaced
```

---

## JULES EXECUTION ORDER
1. **AUDIT** — Run audit, generate `AUDIT_REPORT.md`
2. **CONFIG** — Create/update `config.yaml`, `.env.example`
3. **VIT MEMORY** — Build ChromaDB RAG pipeline first (other modules depend on it)
4. **VIT BRAIN** — Build local LLM client + prompt templates
5. **VIT ENGINE** — Add LSTM alongside existing `.pkl` models
6. **VIT NERVE** — Wire everything into FastAPI orchestrator
7. **VIT SCRAPER** — Upgrade scrapers to feed VITMemory
8. **REQUIREMENTS** — Finalize `requirements.txt` and `render.yaml`

---

## HARD RULES FOR JULES
- ✅ EXTEND existing files — never overwrite working code
- ✅ Preserve all existing `.pkl` model loading logic
- ✅ Preserve all existing CSV data files
- ✅ Keep Replit compatibility where possible during migration
- ❌ NEVER hardcode API keys — use `os.getenv()` always
- ❌ NEVER call OpenAI, Google, DeepSeek, or any external LLM API
- ❌ NEVER install packages that require GPU on Render (CPU only)
- ❌ NEVER delete `vit_data/` contents
