# VIT Integration Matrix

**Date**: 2026-07-08
**Type**: Connectivity Audit

## 1. Integration Status Table

| Integration | Type | Status | Evidence / Note |
| :--- | :---: | :---: | :--- |
| **Wallet ↔ Blockchain** | Core | **Broken** | Depends on `kernel.get_subsystem("blockchain")` which is missing in Kernel. |
| **Wallet ↔ AI** | Optional | **Missing** | No direct link found; AI intelligence not currently used for wallet risk scoring. |
| **AI ↔ Prediction** | Core | **Verified** | AI models generate signals used in the match prediction routes. |
| **Prediction ↔ Storage** | Core | **Partial** | Matches are stored in PostgreSQL; Tachyon integration is available but not the primary path. |
| **Storage ↔ Blockchain** | Core | **Missing** | Tachyon and VIT Chain operate independently; Proof of Storage linkage is a stub. |
| **Identity ↔ Wallet** | Core | **Broken** | Passports exist but are not enforced at the wallet transaction layer. |
| **Identity ↔ Admin** | Core | **Partial** | Admin panel lists users but lacks deep DID verification tools. |
| **Admin ↔ AI** | Core | **Verified** | Admin dashboard (`admin_audit_predictions.py`) heavily utilizes AI signals for auditing. |
| **Scheduler ↔ AI** | Core | **Verified** | `retrain-cron.yml` and `retrain_cron.py` automate AI model retraining. |
| **Governance ↔ Blockchain**| Core | **Partial** | DAO models exist; on-chain execution of proposals is not fully functional. |
| **SDK ↔ Platform** | Core | **Verified** | Python SDK calls FastAPI endpoints for core operations. |
| **Explorer ↔ Node** | Core | **Missing** | Explorer reads from the API, which reads from the DB, not directly from nodes. |
| **Node ↔ Blockchain** | Core | **Verified** | Nodes participate in the P2P network and gossip protocol. |

## 2. Critical Blockers

### A. Kernel Method Regression
The primary integration mechanism for cross-domain communication in VIT is the `kernel.get_subsystem(name)` method. Since this method is missing from `app/core/kernel.py`, almost all high-level integrations (e.g., API -> Blockchain, API -> Wallet) are currently **Broken** at runtime.

### B. Wallet ↔ Blockchain Segregation
While the `WalletSubsystem` lists `blockchain` as a dependency, there is no implemented logic to settle wallet transactions on the `vit_chain` L2 automatically.

### C. Tachyon ↔ Consensus
The intended link where Tachyon storage providers are rewarded via VIT Chain consensus is currently a **Missing** implementation, preventing the "Proof of Storage" from being operational.

---
**Confidence Level**: High (Verified via dependency and call-site analysis).
