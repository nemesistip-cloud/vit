# VIT Network — Product Philosophy & Core Values

**Version:** 6.0.0
**Domain:** /docs/product/
**Status:** Canonical Reference

---

## 1. Core Philosophies

### 1.1 Product Philosophy: The Premium Operating System
We design products that feel less like standard web applications and more like high-performance operating systems (such as Apple's macOS, GitHub, or Linear). We prioritize:
- **High-Density Information:** High-contrast charts, latency logs, and tabular data over empty whitespace.
- **Micro-Actions:** Direct keyboard shortcuts (via a global Command Palette) and low-friction hover cards.
- **Glass-morphic Aesthetics:** Subtle backdrop blurs, dark-first UI structures, and glowing border animations.

### 1.2 Technology Philosophy: Verifiable Monolithic Scalability
- **Engineered Monolith:** We consolidate our core application logic inside a robust, highly modular Python FastAPI backend and React frontend. This minimizes deployment complexity while keeping strict logical boundaries between workspaces.
- **Cryptographic Anchoring:** All state-mutating events are bound to the Base L2 blockchain or the native VIT Chain.
- **Parallel Swarms:** Network nodes run parallelized asynchronous loops to ingest IoT events and write telemetry metrics, preventing blocking bottlenecks.

### 1.3 Community Philosophy: Contribution-Driven Utility
The community is not a group of passive consumers, but active nodes in the ecosystem:
- **Validators:** Earn reward payouts by co-signing predictions and verifying block consensus.
- **Storage Contributors:** Share excess bandwidth and cloud storage space, earning VITCoin on a per-megabyte basis.
- **Academic Collaborators:** Build advanced simulation models and research pipelines, gaining reputation (DID credentials) within the Network Academy.

---

## 2. Dynamic 3-Governor Hybrid Model Principles

VIT Network's native asset, **VITCoin**, is priced and calibrated using a three-governor pricing engine (v6.0.0):

```
       ┌────────────────────────────────────────────────────────┐
       │             HYBRID 3-GOVERNOR PRICING ENGINE           │
       └───────────────────────────┬────────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
  │  GOVERNOR 1  │          │  GOVERNOR 2  │          │  GOVERNOR 3  │
  │ Demand-Ratio │          │ Supply-Ratio │          │  Price-Trend │
  └──────────────┘          └──────────────┘          └──────────────┘
```

1. **Governor 1 (Demand-Ratio):** Incorporates the 24h buy/sell transaction ratio on the exchange, scaling prices upward during intensive buy demand.
2. **Governor 2 (Supply-Ratio):** Evaluates the locked-vs-circulating supply ratio (staking volumes, vault locks), compressing prices upward as circulating supply contracts.
3. **Governor 3 (Price-Trend):** Calculates a rolling historical carry trend (EMA) over the past 30 days to limit artificial price volatility and prevent flash crashes.

---

## 3. Product Success Metrics

To monitor product performance, the platform tracks the following metrics on an ongoing basis:

### 3.1 Trust Metrics
- **Consensus Latency:** Average time in seconds to verify block consensus (Target: $<15s$).
- **Attestation Accuracy:** Percentage of AI predictions certified correct post-settlement (Target: $>75\%$).
- **Challenge Pass Rate:** Percentage of Tachyon VESS storage challenges successfully completed by nodes (Target: $>99.9\%$).

### 3.2 Value Metrics
- **Burn Rate:** Volume of VITCoin burned via gas fees per day.
- **Active Staking Yield:** Volume of tokens locked in validators compared to daily trading volume.
- **Provider Multiplier:** The volume of shared excess storage compared to traditional cloud costs.

---

## 4. Product Decision Scorecard

Feature proposals must be evaluated against our scorecards prior to implementation.

| Rule ID | Criteria | Score (0-3) | Validation Metric |
| :--- | :--- | :--- | :--- |
| **INT-01** | Does the feature incorporate or improve machine-learning intelligence? | | Model accuracy gain / parameter count |
| **TRU-02** | Is the state or transaction anchored cryptographically on-chain? | | Blockchain transaction presence |
| **VAL-03** | Does this generate economic utility or burn token supply? | | Estimated daily VITCoin burn |

If cumulative score is $\ge 7$, the feature is approved for the current roadmap phase. If $<5$, the feature is rejected.
