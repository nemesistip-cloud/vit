# VIT Network — Wallet & VITCoin Audit Report
**Date:** 2025-06-26  
**Version:** 5.5.0  
**Auditor:** Production Readiness Pass

---

## 1. app/modules/wallet/models.py

**What it does:** Defines all SQLAlchemy ORM models for the wallet subsystem.

**Models present:**
- `Wallet` — multi-currency balance store (NGN, USD, USDT, PI, VITCoin, staked VITCoin)
- `WalletProfile` — behavioral analytics per wallet
- `WalletTransaction` — immutable ledger row per credit/debit
- `WalletSubscriptionPlan` / `WalletUserSubscription` — tiered subscription management
- `WithdrawalRequest` — payout requests with status machine
- `SavingsVault` — goal/emergency savings, has `locked_until` but **missing `lock_period_days` column** and **`apy_pct` / `projected_yield` fields**
- `PlatformConfig` / `PlatformSecret` — admin-managed key-value and encrypted secrets
- `VITCoinPriceHistory` — time-series price table
- `WebhookEvent` — audit log for inbound payment webhooks

**Missing models:**
- ❌ `P2POffer` — peer-to-peer offer listing (buy/sell ads)
- ❌ `P2POrder` — executed trade against an offer (escrow + state machine)

**Issues:**
- `SavingsVault.lock_period_days` absent — cannot distinguish 30/90/180/365 day tiers at creation time; only `locked_until` datetime is stored
- No `apy_pct` column on `SavingsVault` — yield cannot be persisted per vault
- `WalletTransaction` has no `description` column — CSV export attempts `tx.description` and silently writes empty strings

---

## 2. app/modules/wallet/routes.py

**What it does:** User-facing wallet REST API (1 179 lines).

**Existing endpoints:**
| Method | Path | Status |
|--------|------|--------|
| GET | /api/wallet/me | ✅ works but wrong path (spec: `/api/wallet`) |
| GET | /api/wallet/vitcoin-balance | ✅ |
| GET | /api/wallet/transactions | ✅ paginated, filterable |
| POST | /api/wallet/deposit/initiate | ✅ Paystack + fallback |
| POST | /api/wallet/deposit/verify | ⚠️ POST not GET, no path param |
| POST | /api/wallet/kyc/submit | ✅ |
| POST | /api/wallet/convert | ✅ but no idempotency key |
| POST | /api/wallet/withdraw | ✅ but missing bank_code/account_name fields, no KYC threshold check |
| GET | /api/wallet/withdraw/status/{id} | ✅ |
| POST | /api/wallet/subscribe | ✅ |
| GET | /api/wallet/plans | ✅ |
| GET | /api/wallet/statement/export | ⚠️ references `tx.description` and `tx.transaction_type` (wrong attribute names) |
| GET | /api/wallet/exchange-rates | ✅ |
| GET | /api/wallet/vitcoin-price | ✅ cached |
| GET | /api/wallet/vitcoin-price/history | ⚠️ max 90 days (spec: 365) |
| GET | /api/wallet/withdrawals | ✅ |
| POST | /api/wallet/telegram/stars-invoice | ✅ |
| POST | /api/wallet/deposit/pi | ✅ |
| POST | /api/wallet/deposit/momo | ✅ |
| Admin KYC routes | various | ✅ |

**Missing endpoints (entire feature groups absent):**
- ❌ GET `/api/wallet` — overview with staked amount, pending withdrawals total, 30d earnings
- ❌ GET `/api/wallet/transactions/{tx_id}` — single transaction detail
- ❌ GET `/api/wallet/deposit/verify/{reference}` — GET variant for manual polling
- ❌ POST `/api/wallet/vitcoin/buy` — buy VITCoin with fiat (with idempotency)
- ❌ POST `/api/wallet/vitcoin/sell` — sell VITCoin for fiat (with idempotency)
- ❌ GET `/api/wallet/vitcoin/price` — separate clean price endpoint (spec path differs)
- ❌ GET `/api/wallet/vitcoin/price/history` — OHLCV, max 365 days
- ❌ POST `/api/wallet/stake` — stake VITCoin
- ❌ POST `/api/wallet/unstake` — unstake VITCoin
- ❌ GET `/api/wallet/stake/status` — staked amount, unlock date, accrued rewards
- ❌ GET `/api/wallet/convert/quote` — dry-run quote, no state change
- ❌ GET/POST/DELETE `/api/wallet/p2p/offers` — P2P offer listing and creation
- ❌ POST `/api/wallet/p2p/orders` — initiate trade
- ❌ POST `/api/wallet/p2p/orders/{id}/confirm-payment` — buyer confirms fiat sent
- ❌ POST `/api/wallet/p2p/orders/{id}/release` — seller releases escrow
- ❌ POST `/api/wallet/p2p/orders/{id}/dispute` — raise dispute
- ❌ GET `/api/wallet/p2p/orders` / `/{id}` — order history and detail
- ❌ GET/POST `/api/wallet/vaults` — savings vault management
- ❌ POST `/api/wallet/vaults/{id}/withdraw` — unlock vault
- ❌ GET `/api/wallet/referral/earnings` — referral VITCoin summary
- ❌ POST `/api/wallet/referral/claim` — claim referral earnings

**Other issues:**
- `withdraw` endpoint accepts `destination` as a free-text field; spec requires `bank_code`, `account_number`, `account_name` separately
- No idempotency key handling on any mutating endpoint
- `deposit/initiate` records the `payment_link` in `tx_metadata` but never checks for duplicate references before inserting
- `convert` and `withdraw` do not use `async with db.begin()` — partial failure can leave wallet in inconsistent state
- KYC threshold check on withdrawals is absent

---

## 3. app/modules/bridge/routes.py

**What it does:** Cross-chain bridge REST API.

**Existing endpoints:**
| Method | Path | Status |
|--------|------|--------|
| GET | /api/bridge/pools | ✅ |
| GET | /api/bridge/pools/{id} | ✅ |
| POST | /api/bridge/initiate | ✅ pool-based model |
| GET | /api/bridge/transactions/my | ✅ |
| GET | /api/bridge/transactions/{id} | ✅ |
| GET | /api/bridge/stats | ✅ |
| POST | /api/bridge/relayer/confirm | ✅ admin |
| GET | /api/bridge/admin/transactions | ✅ admin |

**Missing per spec:**
- ❌ GET `/api/bridge/status` — health + locked liquidity + pending count (currently `stats` differs in shape)
- ❌ POST `/api/bridge/lock` — simplified lock flow with EVM address validation, no pool_id required
- ❌ POST `/api/bridge/unlock` — burn proof verification by tx_hash
- ❌ GET `/api/bridge/transactions` — user history (currently `/transactions/my`)

---

## 4. app/modules/wallet/ws_price.py

**Status:** ❌ File does not exist.  
VITCoin price WebSocket endpoint is completely absent. The frontend has no live price feed.

---

## 5. Frontend — pages/wallet/ and components/wallet/

**Status:** ❌ Directory `frontend/src/pages/wallet/` does not exist.  
**Status:** ❌ Directory `frontend/src/components/wallet/` does not exist.  
**Status:** ❌ `frontend/src/hooks/useWallet.ts` does not exist.

**What exists:**
- `frontend/src/pages/wallet.tsx` — single monolithic page, ~80 lines, shows basic balance cards and transaction list. No staking, no P2P, no bridge, no vaults, no buy/sell.
- `frontend/src/components/wallet-connect-button.tsx` — Web3 MetaMask connect button only, unrelated to wallet pages.

**API hooks present in api-client/index.ts:**
- `useGetWallet` → `/api/wallet/me` (wrong path vs spec)
- `useListTransactions` → `/api/wallet/transactions`
- `useInitiateDeposit`, `useVerifyDeposit`, `useConvertCurrency`, `useWithdraw`
- `useGetVitcoinPrice` → `/api/wallet/vitcoin-price`
- `useTelegramStarsInvoice`

**Missing API hooks:** all buy/sell, staking, P2P, vaults, referral, bridge lock/unlock, quote

**App.tsx routing:**
- Single `/wallet` route mapped to the old `WalletPage`
- No `/wallet/*` sub-routes exist

---

## 6. Summary of Gaps

| Category | Gap Severity |
|----------|-------------|
| P2POffer, P2POrder models | 🔴 Missing entirely |
| lock_period_days on SavingsVault | 🔴 Missing column |
| VITCoin buy/sell endpoints | 🔴 Missing entirely |
| Staking endpoints | 🔴 Missing entirely |
| P2P endpoints | 🔴 Missing entirely |
| Vaults endpoints | 🔴 Missing entirely |
| Referral claim endpoints | 🔴 Missing entirely |
| WebSocket price feed | 🔴 Missing entirely |
| All wallet frontend pages | 🔴 Missing entirely |
| Idempotency on mutations | 🔴 Not implemented |
| Atomic DB transactions | 🟠 Missing on convert/withdraw |
| Bridge lock/unlock endpoints | 🟠 Missing |
| SavingsVault apy_pct field | 🟠 Missing |
| WalletTransaction description field | 🟡 Minor: CSV silently empty |
| GET /api/wallet overview path | 🟡 Path mismatch |
| vitcoin/price history 365d cap | 🟡 Currently 90d |
