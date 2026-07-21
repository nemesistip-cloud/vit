# VIT Network — Workspace Architecture

**Version:** 6.0.0
**Domain:** /docs/workspaces/
**Status:** Design Approved

---

## 1. Purpose & Scope

The VIT Network frontend and backend are designed around the concept of **Workspaces**. A workspace is an isolated, modular sub-environment of the platform shell dedicated to a specific user focus. This architecture guarantees that VIT can scale to 100+ workspaces without code bloat, layout collisions, or database schema degradation.

This document details the capabilities, dependencies, lifecycles, and relationships of the core workspaces in the VIT ecosystem.

---

## 2. Global Workspace Matrix

The workspaces are integrated inside the platform shell and cross-communicate through a secure event bus.

```
       ┌────────────────────────────────────────────────────────┐
       │                   GLOBAL PLATFORM SHELL                │
       └───────────────────────────┬────────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
  │  WORKSPACES  │          │  WORKSPACES  │          │  WORKSPACES  │
  │  • AI Agent  │          │ • Blockchain │          │ • Ecosystem  │
  │  • Sports    │          │ • Explorer   │          │ • Storage    │
  │  • Finance   │          │ • Wallet     │          │ • Developers │
  └──────────────┘          └──────────────┘          └──────────────┘
```

Below is the definitive workspace catalog:

| Workspace | Purpose | Primary Users | Key Capabilities | System Dependencies |
| :--- | :--- | :--- | :--- | :--- |
| **AI Assistant** | Natural-language query interface for ecosystem data | Individual, Enterprise | Intent routing, LLM analytics extraction, wallet drafting | `vit-ai` Service, Redis Cache |
| **Sports Intel** | Verifiable sports prediction analysis & calibration | Pro Traders, Individual | ML weight mapping, fair-odds line charting, CLV analytics | Postgres, Sports Data Feed |
| **Finance Intel** | Advanced prediction market pricing and margin tracking | Businesses, Researchers | Accumulator simulations, portfolio analysis, Kelly staking | Postgres, Wallet Module |
| **Cloud** | Orchestrate cloud provider remnant instances | Developers, Enterprise | Resource mapping, VM deployment, telemetry tracking | Resource Subsystem, Redis |
| **Storage (Tachyon)** | Decentralized, erasure-coded swarm object storage | Individual, Developer | File shredding, fragment download, node linking, quota UI | `tachyon` Daemon, DiskProvider |
| **Marketplace** | Peer-to-peer intelligence trading and signal exchange | Creators, Pro Traders | Signal listing, reputation verification, escrow release | Wallet Module, Identity (DID) |
| **Developer Plat** | Gateway for API key management and SDK documentation | Developers, AI Agents | Key generation, quota limits tracking, webhook settings | Gateway Middleware, Postgres |
| **Governance** | Voting on proposals, validation slashes, and treasury | DAO Members, Validators | Proposal submission, voting weights, validator staking | VIT Chain L2, ValidatorStake |
| **Wallet** | Central banking and multi-currency exchange gateway | All Persona Types | P2P bank escrows, coin conversions, withdrawals | Postgres, Paystack, Stripe |
| **Analytics** | Raw telemetry logs and kernel performance dashboard | Admins, Researchers | Subsystem metrics, DB index checks, Redis capacity | Observability Subsystem, Redis |
| **Automation** | Orchestrate scheduled tasks and agent routines | Enterprise, AI Agents | Task configurations, scheduled event triggers, logs | Celery, Postgres, TaskQueue |
| **Identity (DID)** | Standardized W3C profile and academic verification | Students, Enterprise | DID generation, credential emission, skills ledger | W3C DID Engine, Postgres |
| **Enterprise** | Multi-user corporate intelligence dashboard | Enterprise | Role mapping (RBAC), multi-user auditing, reports | RBAC Subsystem, Postgres |

---

## 3. Workspace Detail Specifications

### 3.1 AI Assistant Workspace
- **Capabilities:**
  - Conversational analytics over sports predictions, wallet balances, and governance votes.
  - Generates transaction drafts (e.g. "Draft a conversion of 100 USDT to VITCoin").
- **Ecosystem Relationships:** Acts as the natural-language gateway to all other workspaces.
- **Expansion Strategy:** Expand model routing to support third-party LLMs (OpenAI, Anthropic) using user-provided API keys.

### 3.2 Sports Intelligence Workspace
- **Capabilities:**
  - Dynamic re-weighting chart for the 13 machine-learning models.
  - Multi-market odds comparisons (Asian Handicap, Correct Score, BTTS).
  - Fair-value edge calculator.
- **Ecosystem Relationships:** Feeds prediction metrics to the Finance Intelligence workspace.
- **Expansion Strategy:** Extend analytics to regional and collegiate sports leagues in Africa.

### 3.3 Storage (Tachyon) Workspace
- **Capabilities:**
  - Drag-and-drop file shredder using Reed-Solomon ($K=6, M=3$).
  - Swarm node dashboard tracking active fragment locations.
  - Storage provider links (Google Drive, Dropbox, Local Storage).
- **Ecosystem Relationships:** Provides model-weight storage for the AI Assistant and `vit-ai` service.
- **Expansion Strategy:** Implement WebDAV compatibility to allow direct network mounting.

---

## 4. Workspace Lifecycle Architecture

To prevent memory leaks and performance degradation in the SPA, workspaces conform to a strict lifecycle:

1. **Mounting Phase (`initialize`):**
   - Retrieve workspace-specific configuration parameters from `PlatformConfig`.
   - Pre-fetch the initial workspace dataset via TanStack Query.
2. **Execution Phase (`active`):**
   - Establish websocket listeners for live-data updates (e.g. odds changes, wallet transactions).
   - Rate limit UI re-renders to a maximum of 24 frames per second.
3. **Dismounting Phase (`destroy`):**
   - Cancel all active, uncompleted HTTP requests using `AbortController`.
   - Close open websocket connections.
   - Flush transient, workspace-specific state from RAM.

---

## 5. Actionable Implementation Guidance

Developers adding new workspaces must inherit from the base React wrapper:

```typescript
interface WorkspaceConfig {
  id: string;
  title: string;
  requiredRole: string;
  onInitialize: () => Promise<void>;
  onDestroy: () => void;
}

export const WorkspaceWrapper: React.FC<WorkspaceConfig> = ({ id, onInitialize, onDestroy, children }) => {
  useEffect(() => {
    onInitialize();
    return () => onDestroy();
  }, [id]);

  return <div className="workspace-container">{children}</div>;
};
```

This clean workspace structure guarantees that the VIT Network portal operates as an unified, performant desktop-class operating system.
