# VIT Network — Workspace Page Designs & Specs

**Version:** 6.0.0
**Domain:** /docs/frontend/
**Status:** Page Specs Approved

---

## 1. Master Dashboard Workspace

- **Purpose:** Serve as the unified command center for individual and enterprise operators, aggregating balances, model accuracy stats, and network telemetry.
- **Features:**
  - Semantic Multi-Currency Balance strip (VIT, USD, USDT).
  - Live model-performance carry chart (Recharts).
  - Pinned workspaces grid.
- **Dashboard Layout:** Top horizontal strip for metrics, central left area for prediction trends, central right panel for the live block proposal feed.
- **Search:** Local filter to search pinned actions or active workspace links.
- **Empty States:** "No assets connected. Click 'Initialize Wallet' to get started." Includes a clear primary CTA.
- **Loading States:** Shimmer bone skeleton frames (`Skeleton`) replacing charts and transaction lists.

---

## 2. AI Assistant Workspace

- **Purpose:** Provide a conversational interface that enables users to query data and queue transactions using natural language.
- **Features:**
  - Conversational chat bubble thread.
  - Quick command suggestions (e.g., "Analyze upcoming Liverpool match", "Show my storage usage").
  - Transaction draft modals (requires TOTP confirm before execution).
- **Navigation:** Deep-links to `/platform/ai`. Sidebar contains conversation history directories.
- **Dashboard Layout:** Left side contains previous chats; central section is the scrollable chat canvas; bottom is the message input container.
- **Interaction Design:** Uses smooth, spring-based scrolling to automatically reveal new replies; typing indicators use dynamic dot-pulse animations.

---

## 3. Sports Intelligence Workspace

- **Purpose:** Analyze and display sports prediction probabilities compiled by the 13-model AI ensemble.
- **Features:**
  - Fairness line chart showing bookmaker margin.
  - Multi-market selector tab (1x2, Asian Handicap, Correct Score, BTTS).
  - 13-model individual weights and calibration scores panel.
- **Dashboard Layout:** Three top-level metric cards (highest confidence match, historical win-rate, total verified matches), center-left grid for fixtures, center-right model calibration chart.
- **Detail Pages:** `/platform/sports/match/{id}` displays historical Head-to-Head trends, weather/injury telemetry, and real-time news sentiments.
- **Create Flow:** CSV fixture upload Wizard for administrators. Includes file mapping columns validation.

---

## 4. Wallet & Financial Rails Workspace

- **Purpose:** Centralized banking portal for depositing, converting, staking, and withdrawing multi-currency assets.
- **Features:**
  - Multi-currency vault lockups with custom APY rates.
  - Conversions panel with real-time exchange rates.
  - Interactive P2P bank transfer escrow wizard.
- **Dashboard Layout:** Left card displays detailed wallet balances; center section is split between conversion and withdraw forms; bottom displays transactional ledgers with *JetBrains Mono* styling.
- **Security Check:** Every withdrawal requires a valid TOTP token input, which checks if `withdrawals_frozen` is `False`.
- **Idempotency Guard:** Submitting any mutation injects `X-Idempotency-Key` headers into the API request client.

---

## 5. Marketplace Workspace

- **Purpose:** Connect signal creators with consumer buyers, facilitating the exchange of accurate prediction metrics.
- **Features:**
  - Seller rating and verified accuracy rating cards.
  - Dynamic prediction signal listing.
  - Automated dispute review drawer.
- **Dashboard Layout:** Grid list of active sellers categorized by verified profit ROI; details display list of open predictions.
- **Create Flow:** "List Signal" Wizard where creators upload their analytical predictions, set an escrow fee, and lock up a slashing stake.

---

## 6. Cloud Workspace

- **Purpose:** Deploy and monitor virtual machine instances utilizing decentralized cloud provider remnants.
- **Features:**
  - Virtual server templates selector.
  - Real-time CPU, RAM, and storage utilization telemetry graphs.
  - Instance log terminal window.
- **Dashboard Layout:** Top section display cluster utilization bars; center displays active VM instances; details page shows log terminals.
- **Create Flow:** Click "New VM Instance", configure size, select region, link storage did, and launch.

---

## 7. Storage (Tachyon) Workspace

- **Purpose:** Securely upload, shred, download, and manage decentralized files utilizing the Reed-Solomon storage swarm.
- **Features:**
  - Drag-and-drop file uploader area.
  - Storage provider sync panel.
  - Quota visual progress bars.
- **Dashboard Layout:** Top row tracks quota bytes used vs remaining; center displays a file directory table; right drawer highlights fragment locations across peer nodes.
- **Upload Flow:** Drag file $\rightarrow$ Shred into $K=6, M=3$ shards $\rightarrow$ Distribute across providers $\rightarrow$ Generate W3C storage proof.

---

## 8. Governance Workspace

- **Purpose:** Allow validator operators and DAO members to propose network upgrades and vote on active parameters.
- **Features:**
  - Proposal list categorized by state (draft, active, passed, executed).
  - Interactive voting weight slider.
  - Slashed validator appeal list.
- **Dashboard Layout:** Left section displaying active proposals; right section displaying staking statistics; details page showing voting progress bars and voter addresses.

---

## 9. Analytics Workspace

- **Purpose:** Monitor the hardware, database indices, and latency of the node.
- **Features:**
  - Core database table row counts list.
  - Redis connection latency telemetry line chart.
  - Active subsystem health checklists.
- **Dashboard Layout:** Dense grid tracking telemetry, query counts per second, API latency logs, and memory capacity bars.

---

## 10. Developer Platform Workspace

- **Purpose:** API credentials gateway and SDK documentation repository.
- **Features:**
  - API Key generator panel.
  - Quota consumption line charts.
  - Interactive webhook registry form.
- **Dashboard Layout:** Left side manages active API keys; right side contains quick-copy REST endpoint definitions; center tracks volume usage metrics.

---

## 11. Enterprise Workspace

- **Purpose:** Multi-user administrative console for organizational node management.
- **Features:**
  - Multi-seat user lists.
  - Explicit role mapping selector (RBAC).
  - Corporate expense report generator.
- **Dashboard Layout:** Table list of authorized users; details panel displaying user-specific action histories.

---

## 12. Settings Workspace

- **Purpose:** Global configuration portal for personal security, notification triggers, and platform parameters.
- **Features:**
  - Personal profile forms.
  - Interactive TOTP 2FA activation wizard.
  - Multi-currency payment method selectors.
- **Dashboard Layout:** Vertical tabs list (Profile, Security, Payments, Notifications); right section displays active forms.
- **Interaction Design:** All saves trigger a subtle green toast notification with an audible alert chime option.
