# VITCoin Monetary Policy Baseline

**Version:** 6.0.0
**Domain:** /docs/governance/
**Status:** Specification only — not enforced in production
**Governance requirement:** REQUIRED before any implementation or chain-enforced supply rule

---

## 1. Purpose and Boundary

This document defines the proposed monetary-policy baseline for VITCoin and the reconciliation rules that should be used while the network is still in governance review. It does not change the live chain state, does not modify minting logic, and does not enforce treasury or burn rules in production.

The authoritative execution layer remains the canonical VIT Chain state. Gateway and database summaries are informational only unless they map directly to chain-validated balances and event records.

> The maximum VITCoin supply remains unresolved and must be approved by governance before any protocol-enforced cap or issuance schedule is implemented.

---

## 2. Canonical Design Principles

1. VIT Chain remains the sole source of truth for balances, burn events, treasury allocations, and validator rewards.
2. Gateway-side financial data may be used for reconciliation, but it must never override chain state.
3. Any monetary rule that changes total supply, fee distribution, burn behavior, or protocol reward schedule is a protocol change and requires governance approval.
4. Treasury, burn, validator, and AI allocations are treated as accounting overlays until governance formally approves them.

---

## 3. Baseline Supply Model (Proposed / Not Enforced)

### 3.1 Initial Genesis Baseline

The current chain baseline assumes the following initial economics:

- Initial genesis mint: 1,000,000 VIT
- Genesis source: special `genesis_mint` transaction
- Treasury allocation baseline: 70% of genesis mint
- Operational / ecosystem allocation baseline: 30% of genesis mint

This yields:

$$
S_{genesis} = 1{,}000{,}000
$$

$$
S_{treasury} = 0.70 \times S_{genesis} = 700{,}000
$$

$$
S_{ops} = 0.30 \times S_{genesis} = 300{,}000
$$

and the invariant:

$$
S_{genesis} = S_{treasury} + S_{ops}
$$

### 3.2 Unresolved Policy Parameter

The protocol architecture explicitly leaves the maximum supply open until governance determines whether VITCoin should be:

- fixed supply,
- inflationary with scheduled emissions,
- deflationary with burn-and-rebate mechanics,
- or a hybrid of capped issuance plus burn-based reduction.

Until the governance decision is recorded and implemented, the network may only operate with the design statement:

- current chain-state balances are valid,
- no new supply cap is enforced,
- no issuance schedule is activated,
- no production burn policy is forced.

---

## 4. Proposed Fee and Treasury Reconciliation Model

The following distribution model is a baseline design only. It is not a live enforcement rule and must not be hard-coded as a production monetary policy without governance review.

### 4.1 Distribution Shares

- Validator share: 40%
- Treasury share: 30%
- Burn share: 20%
- AI and platform share: 10%

This yields:

$$
S_{validator} = 0.40 \times F
$$

$$
S_{treasury} = 0.30 \times F
$$

$$
S_{burn} = 0.20 \times F
$$

$$
S_{ai} = 0.10 \times F
$$

where $F$ is the total protocol fee volume in a given settlement interval.

### 4.2 Reconciliation Rule

During reconciliation, the system should verify:

$$
F = S_{validator} + S_{treasury} + S_{burn} + S_{ai}
$$

with the requirement that each component is traceable to either:

- a chain transaction event,
- a block reward summary,
- a treasury ledger record,
- or a burn log event.

Gateway accounting may aggregate these values for reporting, but the canonical source must remain the chain event stream and persisted ledger state.

---

## 5. Supply Integrity Rules

The following rules are specification-only guardrails for future governance and implementation work:

1. Every mint must be attributable to a canonical chain event.
2. Every burn must be explicitly recorded and persisted.
3. Treasury balances must reconcile to canonical chain state and not to separately managed gateway balances.
4. The chain must reject supply updates that cannot be traced to a single final, validated block.
5. Any supply policy that affects total VITCoin in circulation is a protocol parameter and must be approved in governance before enforcement.

---

## 6. Reconciliation Standard

The production environment should reconcile monetary values as follows:

- Chain balance: authoritative ledger balance for wallet addresses
- Treasury summary: informative service-level view of treasury operations
- Burn summary: aggregate of provable burn events only
- Validator rewards: computed from canonical block rewards and fee allocations
- AI payouts: deterministic service allocations, if and when approved

Any mismatch between the chain and gateway-level summaries must be treated as a reconciliation issue, not as a source of truth override.

---

## 7. Implementation Status

This document is intentionally design-only. It does not authorize the following actions:

- automatic supply caps,
- live burn mechanics,
- treasury locking by code,
- validator reward policy enforcement,
- or any chain-wide issuance schedule.

The current implementation remains the canonical chain plus chain-safe read adapters, while monetary policy remains a governance-controlled change set.

---

## 8. Governance Decision Gate

The following decisions are required before this baseline becomes executable protocol policy:

1. final maximum supply cap;
2. issuance schedule, if any;
3. treasury lock and unlock rules;
4. burn cadence and burn trigger conditions;
5. validator reward split policy;
6. AI and platform allocation scope;
7. reconciliation and reporting requirements.

Only once these parameters are approved should the team implement them in the canonical chain logic, not in gateway accounting alone.
