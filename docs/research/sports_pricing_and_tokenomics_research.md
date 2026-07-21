# VIT Network — Sports Pricing & Tokenomics Research

**Version:** 6.0.0
**Domain:** /docs/research/
**Status:** Approved Reference

---

## 1. Executive Summary

This research paper outlines the mathematical pricing and tokenomics engine of the VIT Network (v6.0.0). The native utility asset, **VITCoin**, serves as the primary currency for staking, validator rewards, P2P signal escrows, and storage quotas. Rather than relying on simple market orderbooks, VIT uses a **3-Governor Hybrid Model** to calculate dynamic asset valuations.

---

## 2. Tokenomics Structure & Supply Mechanics

### 2.1 Core Supply Variables
- **Max Supply ($S_{\text{max}}$):** $10,000,000$ VITCoin (fixed, hard-coded).
- **Initial Supply ($S_{\text{genesis}}$):** $1,000,000$ VITCoin.
- **Gas Fee Burn:** $50\%$ of all transaction gas fees are permanently burned, creating a deflationary mechanism as network activity scales.

### 2.2 Staking Mechanics
To host a validator node or list signals in the marketplace, participants must lock a minimum stake ($ST_{\text{min}}$) of **$10,000$ VITCoin**. In return, validators earn block rewards derived from gas fees and a $3\%$ operational reserve allocation.

---

## 3. The 3-Governor Hybrid Pricing Engine Formulas

The spot valuation of VITCoin ($P_{\text{VIT}}$) is calculated dynamically by the node's pricing module utilizing three independent governors:

```
                          ┌───────────────────────────┐
                          │     P_VIT SPOT PRICING    │
                          └─────────────┬─────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
   ┌──────────────┐             ┌──────────────┐             ┌──────────────┐
   │  GOVERNOR 1  │             │  GOVERNOR 2  │             │  GOVERNOR 3  │
   │ Demand-Ratio │             │ Supply-Ratio │             │  Price-Trend │
   │    G_dem     │             │    G_sup     │             │    G_car     │
   └──────────────┘             └──────────────┘             └──────────────┘
```

The unified pricing function is defined as:
$$P_{\text{VIT}} = P_{\text{base}} \times G_{\text{dem}} \times G_{\text{sup}} \times G_{\text{car}}$$

---

### 3.1 Governor 1: Demand Signal ($G_{\text{dem}}$)
Evaluates the ratio of buy volume ($V_{\text{buy}}$) to sell volume ($V_{\text{sell}}$) over a rolling 24-hour window on the internal exchange:
$$G_{\text{dem}} = 1 + \tanh\left( \alpha \times \frac{V_{\text{buy}} - V_{\text{sell}}}{V_{\text{buy}} + V_{\text{sell}} + \epsilon} \right)$$
- **$\alpha$:** Sensitivity constant (default: $0.15$).
- **$\epsilon$:** Small constant to prevent divide-by-zero errors.
- **Behavior:** Symmetrically bounds demand scaling between $[0.85, 1.15]$.

---

### 3.2 Governor 2: Supply Compression ($G_{\text{sup}}$)
Measures the volume of tokens currently locked in validators and savings vaults ($S_{\text{locked}}$) relative to the total circulating supply ($S_{\text{circ}}$):
$$G_{\text{sup}} = e^{\beta \times \left( \frac{S_{\text{locked}}}{S_{\text{circ}}} \right)}$$
- **$\beta$:** Supply multiplier constant (default: $0.25$).
- **Behavior:** As more tokens are staked, available market supply contracts, exponentially scaling the token price upward.

---

### 3.3 Governor 3: Momentum Carry ($G_{\text{car}}$)
Integrates a 30-day exponential moving average (EMA) of historical prices to buffer against speculative spikes and stabilize the network against flash crashes:
$$G_{\text{car}} = \gamma \times \frac{\text{EMA}_{30}(P_{\text{VIT}})}{P_{\text{base}}} + (1 - \gamma)$$
- **$\gamma$:** Momentum carry weight (default: $0.40$).
- **Behavior:** Acts as a stabilizing anchor, limiting sudden price fluctuations.

---

## 4. Economic Security & Slashing

To ensure the integrity of the data signals, the network employs **accuracy-based slashing**:
- If an enterprise validator signs a block containing an AI prediction with a calibration error exceeding $0.25$ (25% variance from actual settled outcome), a $5\%$ portion of their staked capital is slashed.
- Slashed tokens are split: $50\%$ is sent to the Community Treasury; $50\%$ is permanently burned, directly enhancing the value of remaining circulating tokens.
