# 03 Bounding Contexts & Domain Ownership

## 1. Domain Map
The VIT Network is partitioned into the following strict ownership domains:

| Domain | Owner | Key Responsibilities | Allowed Write Paths |
| :--- | :--- | :--- | :--- |
| **Identity** | Identity | Auth, KYC, DID, Community | `app/auth`, `app/modules/auth`, `app/modules/kyc`, `app/modules/did` |
| **AI** | AI | Models, Agents, Inference | `app/ai`, `app/agents`, `app/modules/ai`, `services/ml_service` |
| **Core** | Core | API Gateway, Governance, Sports | `app/core`, `app/api`, `app/modules/governance`, `app/modules/sports` |
| **Database** | Database | Schema, Migrations | `app/db`, `alembic/` |
| **Blockchain** | Blockchain | Wallets, Treasury, Smart Contracts | `packages/contracts`, `app/modules/wallet`, `app/modules/blockchain` |
| **Tachyon** | Tachyon | Decentralized Storage | `tachyon/`, `tachyon_loop.py` |
| **Frontend** | Frontend | UI/UX, Institutional Terminals | `frontend/` |
| **Infrastructure** | Infrastructure | CI/CD, Terraform, Config | `infrastructure/`, `scripts/`, `Dockerfile`, `requirements.txt` |
| **Task** | Task | Background Jobs, Workers | `app/tasks`, `app/worker` |
| **Docs** | Docs | Architecture, Constitution | `docs/`, `README.md`, `.engineering/` |

## 2. Path Restrictions
- **No Cross-Domain Editing**: Agents must only modify files within their assigned domain ownership.
- **Main Entrypoint Guard**: Only the **INTEGRATION ENGINE** is allowed to modify `main.py`, cross-domain routing, and system wiring.
