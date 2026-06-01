# VIT — Professional Analytics & Prediction Platform

[![Version](https://img.shields.io/badge/Version-5.2.0-blue.svg)](https://github.com/nemesistip-cloud/vit)
[![Blockchain](https://img.shields.io/badge/Blockchain-Base_L2-emerald.svg)](https://base.org)
[![AI](https://img.shields.io/badge/AI-13_Model_Ensemble-orange.svg)](app/modules/ai)
[![Deployment](https://img.shields.io/badge/Deploy-Google_Cloud_Run-4285F4.svg)](https://cloud.google.com/run)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

VIT is a professional analytics platform combining machine learning ensembles, autonomous data agents, and blockchain settlement to deliver verifiable, high-confidence predictions for sports and financial markets.

---

## 🚀 Overview

- **ML Ensemble**: 13 calibrated models providing multi-layered signal analytics.
- **Autonomous Agents**: 22 specialized agents for real-time data tracking and validation.
- **Blockchain Core**: Transparent settlement and identity via Base L2.
- **GCP Native**: Built for scale on Google Cloud Run and Cloud SQL.

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (Production) / SQLite (Dev)
- **ML**: Scikit-learn, XGBoost, PyTorch
- **Blockchain**: Web3.py (Base L2)

### Frontend
- **Framework**: React 19 + Vite 6
- **Styling**: Tailwind CSS v4
- **State**: TanStack Query v5

---

## 📦 Quick Start

### Setup

```bash
# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Start application
bash scripts/start_fullstack.sh
```

---

## ☁️ Deployment

VIT is optimized for **Google Cloud Platform**. See [DEPLOYMENT_GCP.md](DEPLOYMENT_GCP.md) for detailed instructions on Cloud Run, Cloud Build, and Secret Manager setup.

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.
