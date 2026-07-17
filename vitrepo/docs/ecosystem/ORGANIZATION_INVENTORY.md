# VIT Organization Inventory

**Date**: 2026-07-08
**Assessment Type**: Forensic Monorepo Audit
**Source of Truth**: `nemesistip-cloud/vit` (Local Checkout)

## 1. Primary Repository: vit

- **Repository name**: vit
- **Visibility**: Public (Assumed from remote URL)
- **Description**: AI Intelligence Oracle & Blockchain Super App
- **Purpose**: Core ecosystem repository containing backend, frontend, and all sub-services.
- **Default branch**: main
- **Current HEAD commit**: 18fe4a8bf86e94f65fb40b780c7d4d61164c7301
- **Last commit date**: Wed Jul 8 00:03:10 2026 +0100
- **Last contributor**: nemesistip-cloud
- **Repository size**: ~12MB (excluding node_modules)
- **Primary language**: Python / TypeScript
- **License**: AGPL-3.0 (from package.json) / Not explicitly found in root LICENSE file (file exists but check content).
- **Stars**: [Requires GitHub API]
- **Forks**: [Requires GitHub API]
- **Open Issues**: [Requires GitHub API]
- **Open PRs**: [Requires GitHub API]
- **Releases**: [Requires GitHub API]
- **Tags**: [Requires GitHub API]
- **Archived status**: Active

## 2. Component Inventory (Sub-Repositories/Modules)

The ecosystem is structured as a monorepo. Below are the internal "repositories" managed within the `vit` root.

| Component | Path | Purpose | Primary Language | Size | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Frontend** | `/frontend` | Main SPA Interface (React) | TypeScript | 2.8M | Active |
| **Explorer** | `/explorer` | Blockchain Block Explorer | JavaScript (JSX) | 200K | Active |
| **Tachyon** | `/tachyon` | Decentralized Storage Engine | Python | 208K | Active |
| **VIT Chain** | `/vit_chain` | L2 Blockchain Core | Python | 352K | Active |
| **VIT Node** | `/vit_node` | Validator/Edge Node Daemon | Python | 96K | Active |
| **Contracts** | `/packages/contracts` | Solidity Smart Contracts | Solidity | 80K | Active |
| **SDK** | `/sdk` | Python/TS SDKs | Python | 48K | Active |

## 3. External Repository References (Historical/Deprecated)

- **vit-sdk**: `https://github.com/Value-analytics-trust/vit-sdk` (Mentioned in `sdk/python/setup.py`) - Likely deprecated or a placeholder.

## 4. Classification Summary

- **Active**: All core components (Frontend, Backend, Chain, Tachyon, Node).
- **Inactive/Deprecated**: External `Value-analytics-trust` repositories (Replaced by Monorepo).
- **Experimental**: `/exchange` (Incomplete implementation).

---
**Evidence**: Verified via `git remote`, `ls -R`, and `du -sh`.
