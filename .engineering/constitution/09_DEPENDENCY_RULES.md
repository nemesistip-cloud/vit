# 09 Dependency Rules

## 1. System Topology
The system follows a strict dependency hierarchy to prevent circular references:

1. **Frontend** depends on **Main Application (API)**.
2. **Main Application** depends on **Database** and **Packages**.
3. **Tachyon Engine** integrates with **Main Application** via API and reads/writes to **Database**.
4. **Infrastructure** deploys all components.

## 2. Package Management
- **Monorepo**: Shared logic lives in `packages/` (e.g., `@vit/sdk`).
- **Python**: Dependencies are managed via `requirements.txt` and `pyproject.toml`.
- **Node.js**: Dependencies are managed via `pnpm`.

## 3. Third-Party Restrictions
- Use official GCP SDKs for cloud services.
- Minimize external dependencies in core modules.
- All new dependencies must be audited for security and license compatibility.
