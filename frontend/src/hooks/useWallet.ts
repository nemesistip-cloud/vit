import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiDelete } from "@/lib/apiClient";
import { toast } from "sonner";

export interface WalletOverview {
  vitcoin_balance: number;
  ngn_balance: number;
  usd_balance: number;
  usdt_balance: number;
  pi_balance: number;
  staked_vitcoin: number;
  pending_withdrawals_total: number;
  earnings_30d: number;
  total_balance_usd: number;
  is_frozen: boolean;
  kyc_verified: boolean;
  vitcoin_price_usd: number;
}

export interface VITPrice {
  price_usd: number;
  price_ngn: number;
  price_usdt: number;
  price_pi: number;
  change_24h_pct: number;
  price_7d: number[];
  circulating_supply: number;
  market_cap_usd: number;
}

export interface WalletTx {
  id: string;
  type: string;
  currency: string;
  amount: number;
  direction: "credit" | "debit";
  status: string;
  reference: string | null;
  description: string | null;
  fee_amount: number;
  created_at: string;
  processed_at: string | null;
}

export interface P2POffer {
  id: string;
  offer_type: "buy" | "sell";
  currency: string;
  available_amount: number;
  rate_ngn: number;
  min_order: number;
  max_order: number;
  payment_method: string;
  user_id: number;
  created_at: string;
}

export interface P2POrder {
  id: string;
  offer_id: string;
  buyer_id: number;
  seller_id: number;
  amount: number;
  rate_ngn: number;
  fiat_total_ngn: number;
  status: string;
  my_role: "buyer" | "seller";
  created_at: string;
  completed_at: string | null;
}

export interface SavingsVault {
  id: string;
  name: string;
  currency: string;
  amount: number;
  lock_period_days: number;
  apy_pct: number;
  locked_until: string | null;
  unlocked: boolean;
  projected_yield: number;
  created_at: string;
}

export interface StakeStatus {
  staked_amount: number;
  vitcoin_balance: number;
  validator_eligible: boolean;
  apy_pct: number;
  estimated_daily_reward: number;
  unlock_date: string | null;
}

export interface BridgeTx {
  id: number;
  tx_hash: string;
  direction: string;
  amount_in: string;
  amount_out: string;
  fee: string;
  status: string;
  destination_address: string;
  created_at: string;
  completed_at: string | null;
}

export function useWalletOverview() {
  return useQuery<WalletOverview>({
    queryKey: ["wallet", "overview"],
    queryFn: () => apiGet("/api/wallet"),
    staleTime: 15_000,
  });
}

export function useVITPrice() {
  return useQuery<VITPrice>({
    queryKey: ["wallet", "vitcoin-price"],
    queryFn: () => apiGet("/api/wallet/vitcoin/price"),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useVITPriceHistory(days = 30) {
  return useQuery<{ history: { date: string; price_usd: number }[]; days: number }>({
    queryKey: ["wallet", "vitcoin-price-history", days],
    queryFn: () => apiGet(`/api/wallet/vitcoin/price/history?days=${days}`),
    staleTime: 300_000,
  });
}

export function useTransactions(page = 1, currency?: string, type?: string) {
  const params = new URLSearchParams({ page: String(page), limit: "20" });
  if (currency) params.set("currency", currency);
  if (type) params.set("transaction_type", type);
  return useQuery<{ transactions: WalletTx[]; total: number; page: number }>({
    queryKey: ["wallet", "transactions", page, currency, type],
    queryFn: () => apiGet(`/api/wallet/transactions?${params}`),
    staleTime: 15_000,
  });
}

export function useStakeStatus() {
  return useQuery<StakeStatus>({
    queryKey: ["wallet", "stake-status"],
    queryFn: () => apiGet("/api/wallet/stake/status"),
    staleTime: 30_000,
  });
}

export function useP2POffers(offerType?: string, currency = "VITCoin", page = 1) {
  const params = new URLSearchParams({ currency, page: String(page), limit: "20" });
  if (offerType) params.set("offer_type", offerType);
  return useQuery<{ offers: P2POffer[] }>({
    queryKey: ["wallet", "p2p-offers", offerType, currency, page],
    queryFn: () => apiGet(`/api/wallet/p2p/offers?${params}`),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function useP2POrders(status?: string) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  return useQuery<{ orders: P2POrder[] }>({
    queryKey: ["wallet", "p2p-orders", status],
    queryFn: () => apiGet(`/api/wallet/p2p/orders?${params}`),
    staleTime: 15_000,
  });
}

export function useVaults() {
  return useQuery<{ vaults: SavingsVault[] }>({
    queryKey: ["wallet", "vaults"],
    queryFn: () => apiGet("/api/wallet/vaults"),
    staleTime: 30_000,
  });
}

export function useBridgeTxHistory() {
  return useQuery<BridgeTx[]>({
    queryKey: ["bridge", "transactions"],
    queryFn: () => apiGet("/api/bridge/transactions"),
    staleTime: 30_000,
  });
}

export function useExchangeRates() {
  return useQuery<{
    rates: Record<string, { rate_to_usd: number; symbol: string; label: string }>;
    ngn_per_usd: number;
    vit_price_usd: number;
  }>({
    queryKey: ["wallet", "exchange-rates"],
    queryFn: () => apiGet("/api/wallet/exchange-rates"),
    staleTime: 60_000,
  });
}

export function useConversionQuote(fromCurrency: string, toCurrency: string, amount: number) {
  return useQuery<{ from_amount: number; received_amount: number; fee: number; fee_pct: number; rate: number }>({
    queryKey: ["wallet", "conversion-quote", fromCurrency, toCurrency, amount],
    queryFn: () =>
      apiGet(
        `/api/wallet/convert/quote?from_currency=${fromCurrency}&to_currency=${toCurrency}&amount=${amount}`
      ),
    enabled: amount > 0 && fromCurrency !== toCurrency,
    staleTime: 25_000,
  });
}

export function useReferralEarnings() {
  return useQuery<{
    referral_count: number;
    total_earned_vitcoin: number;
    pending_claimable: number;
    total_claimed: number;
  }>({
    queryKey: ["wallet", "referral-earnings"],
    queryFn: () => apiGet("/api/wallet/referral/earnings"),
    staleTime: 60_000,
  });
}

function idempotencyKey() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function useBuyVITCoin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { amount_ngn?: number; amount_usd?: number }) =>
      apiPost("/api/wallet/vitcoin/buy", body),
    onSuccess: () => {
      toast.success("VITCoin purchased");
      qc.invalidateQueries({ queryKey: ["wallet"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useSellVITCoin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vitcoin_amount: number) =>
      apiPost("/api/wallet/vitcoin/sell", { vitcoin_amount }),
    onSuccess: () => {
      toast.success("VITCoin sold");
      qc.invalidateQueries({ queryKey: ["wallet"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useStakeVITCoin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (amount: number) => apiPost("/api/wallet/stake", { amount }),
    onSuccess: () => {
      toast.success("VITCoin staked");
      qc.invalidateQueries({ queryKey: ["wallet"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useUnstakeVITCoin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (amount: number) => apiPost("/api/wallet/unstake", { amount }),
    onSuccess: () => {
      toast.success("VITCoin unstaked");
      qc.invalidateQueries({ queryKey: ["wallet"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useConvertCurrency() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { from_currency: string; to_currency: string; amount: number }) =>
      apiPost("/api/wallet/convert", body),
    onSuccess: () => {
      toast.success("Conversion successful");
      qc.invalidateQueries({ queryKey: ["wallet"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useInitiateDeposit() {
  return useMutation({
    mutationFn: (body: { currency: string; amount: number; method: string }) =>
      apiPost<{ payment_link: string; reference: string }>("/api/wallet/deposit/initiate", body),
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useWithdraw() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      amount: number;
      currency: string;
      bank_code?: string;
      account_number?: string;
      account_name?: string;
      destination_type?: string;
    }) => apiPost("/api/wallet/withdraw", body),
    onSuccess: () => {
      toast.success("Withdrawal request submitted");
      qc.invalidateQueries({ queryKey: ["wallet"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useCreateP2POffer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      offer_type: string;
      amount: number;
      currency: string;
      rate_ngn: number;
      min_order: number;
      max_order: number;
      payment_method: string;
      payment_details?: Record<string, string>;
    }) => apiPost("/api/wallet/p2p/offers", body),
    onSuccess: () => {
      toast.success("Offer created");
      qc.invalidateQueries({ queryKey: ["wallet", "p2p-offers"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useCancelP2POffer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (offerId: string) => apiDelete(`/api/wallet/p2p/offers/${offerId}`),
    onSuccess: () => {
      toast.success("Offer cancelled");
      qc.invalidateQueries({ queryKey: ["wallet", "p2p-offers"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useCreateP2POrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { offer_id: string; amount: number }) =>
      apiPost("/api/wallet/p2p/orders", body),
    onSuccess: () => {
      toast.success("Order placed");
      qc.invalidateQueries({ queryKey: ["wallet", "p2p-orders"] });
      qc.invalidateQueries({ queryKey: ["wallet", "p2p-offers"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useP2PConfirmPayment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (orderId: string) =>
      apiPost(`/api/wallet/p2p/orders/${orderId}/confirm-payment`),
    onSuccess: () => {
      toast.success("Payment confirmed");
      qc.invalidateQueries({ queryKey: ["wallet", "p2p-orders"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useP2PReleaseEscrow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (orderId: string) =>
      apiPost(`/api/wallet/p2p/orders/${orderId}/release`),
    onSuccess: () => {
      toast.success("Escrow released");
      qc.invalidateQueries({ queryKey: ["wallet"] });
      qc.invalidateQueries({ queryKey: ["wallet", "p2p-orders"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useCreateVault() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { amount: number; currency: string; lock_period_days: number }) =>
      apiPost("/api/wallet/vaults", body),
    onSuccess: () => {
      toast.success("Savings vault created");
      qc.invalidateQueries({ queryKey: ["wallet"] });
      qc.invalidateQueries({ queryKey: ["wallet", "vaults"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useWithdrawVault() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vaultId: string) =>
      apiPost(`/api/wallet/vaults/${vaultId}/withdraw`),
    onSuccess: () => {
      toast.success("Vault withdrawn successfully");
      qc.invalidateQueries({ queryKey: ["wallet"] });
      qc.invalidateQueries({ queryKey: ["wallet", "vaults"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useBridgeLock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { amount: number; destination_address: string }) =>
      apiPost("/api/bridge/lock", body),
    onSuccess: () => {
      toast.success("VITCoin locked. Awaiting ERC-20 mint on Base L2.");
      qc.invalidateQueries({ queryKey: ["wallet"] });
      qc.invalidateQueries({ queryKey: ["bridge"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useBridgeUnlock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { tx_hash: string; amount: number }) =>
      apiPost("/api/bridge/unlock", body),
    onSuccess: () => {
      toast.success("VITCoin unlocked and credited.");
      qc.invalidateQueries({ queryKey: ["wallet"] });
      qc.invalidateQueries({ queryKey: ["bridge"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useClaimReferralEarnings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost("/api/wallet/referral/claim"),
    onSuccess: () => {
      toast.success("Referral earnings claimed");
      qc.invalidateQueries({ queryKey: ["wallet"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}
