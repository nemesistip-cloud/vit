# VIT Network

### Verifiable intelligence for real-world decisions

![VIT Network](https://img.shields.io/badge/VIT%20Network-Verifiable%20Intelligence-0b7285?style=for-the-badge&labelColor=102a43)
![Production](https://img.shields.io/badge/production-Render-2f855a?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-AGPL--3.0-102a43?style=flat-square)

VIT Network is a production monorepo for verifiable intelligence services. It combines live data ingestion, evidence-aware prediction, autonomous analysis, decentralized storage, and VIT Chain settlement into one observable ecosystem.

The operating principle is simple: **no evidence, no claim**. Every prediction is expected to carry source provenance, feature completeness, model metadata, and an explicit unavailable state when the data is not sufficient.

## Explore the ecosystem

| Surface | Role | Link |
| --- | --- | --- |
| **VIT Network** | Main application, APIs, sports intelligence, wallet and marketplace | [Live app](https://vitnetwork-nls4.onrender.com) |
| **VIT AI** | Intelligence and orchestration services | [Service](https://vit-ai.onrender.com) |
| **VIT Chain** | Standalone chain and settlement layer, Chain ID 7764 | [Service](https://vit-chain.onrender.com) |
| **Tachyon** | Verifiable distributed storage fabric | [Service](https://vit-storage-4trt.onrender.com) |
| **VIT SDK** | Python client for application and chain integrations | [SDK guide](sdk/README.md) |
| **VIT Node** | Community storage and network participation client | [Node guide](vit_node/README.md) |

## What this repository contains

- **Intelligence**: live sports data, historical result providers, odds reconciliation, feature engineering, ensemble inference, and evidence snapshots.
- **Agent systems**: scheduled ingestion, anomaly detection, audit, reporting, and operational coordination.
- **Platform services**: FastAPI APIs, PostgreSQL persistence, Redis-backed caching, authentication, wallet rails, and admin tooling.
- **Storage and chain integration**: Tachyon coordination, provider-backed storage workflows, VIT Chain clients, attestations, and settlement boundaries.
- **Frontend**: the React/Vite application in [`frontend/`](frontend/).

## Prediction integrity

The sports prediction path is deliberately fail-closed:

```text
Live sources -> Match Intelligence Profile -> validation -> features
	-> ensemble -> prediction -> evidence snapshot -> audit/provenance
```

Predictions are not generated merely because an endpoint is available. The pipeline requires sufficient fixture identity, current market data where required, real historical samples, fresh evidence, and a ready model path. When those conditions are not met, the API returns `unavailable` with the reasons and provider state.

## Run locally

```bash
git clone https://github.com/nemesistip-cloud/vit.git
cd vit
python -m venv .venv
source .venv/bin/activate
pip install .

The backend packages live under `backend/`; development commands should use
`PYTHONPATH=backend:.` when running repository scripts directly.
cp .env.example .env
uvicorn main:app --reload
```

For the frontend:

```bash
cd frontend
npm install
npm run dev
```

Configuration is loaded through [`app/config.py`](app/config.py). Never commit secrets; use `.env.example` as the configuration index.

## Verify changes

```bash
pytest -q
python -m compileall -q app
```

The repository also includes focused checks for provider health, evidence quality, prediction provenance, migrations, and frontend behavior. See [`docs/QUALITY_ASSURANCE_AGENT_PROMPT.md`](docs/QUALITY_ASSURANCE_AGENT_PROMPT.md) for the verification playbook.

## Deploy

The production service is containerized and deployed on Render. Pushing to `main` triggers the configured deployment in [`render.yaml`](render.yaml). Database migrations run as part of the production startup path.

## Documentation map

- [Architecture map](docs/archive/VIT_ECOSYSTEM_ARCHITECTURE_MAP.md)
- [Data lineage](docs/archive/VIT_ECOSYSTEM_DATA_LINEAGE.md)
- [Implementation matrix](docs/archive/VIT_ECOSYSTEM_IMPLEMENTATION_MATRIX.md)
- [Security policy](SECURITY.md)
- [Environment variables](ENV_VARS.md)
- [Next phase](NEXT_PHASE.md)

## Brand

**VIT Network — Verifiable Intelligence. Universal Trust.**

The name stands for **Value, Intelligence, Trust**: useful outputs, inspectable reasoning, and accountable infrastructure.
