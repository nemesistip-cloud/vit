# Documentation Alignment Report

## 1. Overview
The documentation in `.engineering/` provides a comprehensive high-level view of the system's intended architecture. However, significant drift exists between these documents and the actual implementation following the v1.1 refactor.

## 2. Identified Drift

### A. Modular Integration (Kernel vs. main.py)
- **Documented**: `VIT_RUNTIME_KERNEL.md` and `LIFECYCLE_ARCHITECTURE.md` describe a system where all modules are orchestrated via the Kernel.
- **Actual**: `main.py` still contains manual route registration and import logic for several core systems (Auth, Identity, Blockchain).
- **Drift**: High. The Kernel is active but its capability to dynamically mount routers is not yet fully utilized in `main.py`.

### B. Module Contracts & Topology
- **Documented**: `contracts.json` and `topology.json` are missing recent foundational platforms:
  - **Resource Platform** (ADR-011)
  - **Persistence Platform** (ADR-010)
  - **Blockchain Platform Service** (ADR-012)
  - **Wallet Platform** (ADR-013A)
- **Drift**: Medium. The ADRs exist, but the central state files (`contracts.json`, `topology.json`) have not been updated to reflect these new "Institutional" entities.

### C. Undocumented APIs
- Several internal SDKs (e.g., `WalletSDK`, `BlockchainSDK`) are implemented but lack corresponding entries in `MODULE_REGISTRY.md` or `contracts.json`.

## 3. Stale ADRs
- **ADR-001-GCP-NATIVE.md**: While GCP remains a target, the current primary deployment is Render. The ADR should be updated to reflect a multi-cloud or platform-agnostic approach with Render as the lead production environment.

## 4. Recommendations
1. **Sync State Files**: Update `contracts.json` and `topology.json` with the 4 new foundational platforms.
2. **Registry Update**: Append new modules and their capabilities to `MODULE_REGISTRY.md`.
3. **Architecture Update**: Revise `main.py` description in `VIT_RUNTIME_KERNEL.md` to reflect its current hybrid state.
