import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import type {
  User, Match, Prediction, Wallet, Transaction,
  Validator, TrainingJob, DashboardSummary
} from "./schemas";

export type { User, Match, Prediction, Wallet, Transaction, Validator, TrainingJob, DashboardSummary };

export const API = {
  me: "/auth/me",
  login: "/auth/login",
  register: "/auth/register",
  dashboard: {
    summary: "/api/dashboard/summary",
    vitcoinPrice: "/api/dashboard/vitcoin-price",
    recentActivity: "/api/dashboard/recent-activity",
  },
  matches: "/matches/upcoming",
  matchesExplore: "/matches/explore",
  matchesRecent: "/matches/recent",
  match: (id: string) => `/matches/${id}`,
  predictions: "/history",
  ticketMarkets: "/history/ticket/markets",
  ticketCandidates: "/history/ticket/candidates",
  ticketBuild: "/history/ticket/build",
  analyticsMyStats: "/analytics/my",
  training: {
    // Real ML training pipeline (app/api/routes/training.py, prefix `/training`)
    jobs: "/training/jobs",
    upload: "/training/dataset/upload",
    progress: (id: string) => `/training/progress/${id}`,
    promote: "/training/promote",
    rollback: "/training/rollback",
    // Module D dataset-scoring helper (app/modules/training/routes.py, prefix `/api/training`)
    score: "/api/training/score",
    prompt: (id: string) => `/api/training/prompt/${id}`,
    modelPerformance: "/api/dashboard/model-confidence",
  },
  validators: "/api/blockchain/validators",
  economy: "/api/blockchain/economy",
  myValidator: "/api/blockchain/validators/my",
  applyValidator: "/api/blockchain/validators/apply",
  validatorPredict: "/api/blockchain/validators/predict",
  stake: (matchId: string) => `/api/blockchain/predictions/${matchId}/stake`,
  myStakes: "/api/blockchain/stakes/my",
  consensusPrediction: (matchId: string) => `/api/blockchain/predictions/${matchId}`,
  wallet: "/api/wallet/me",
  transactions: "/api/wallet/transactions",
  depositInitiate: "/api/wallet/deposit/initiate",
  depositVerify: "/api/wallet/deposit/verify",
  convert: "/api/wallet/convert",
  withdraw: "/api/wallet/withdraw",
  plans: "/api/wallet/plans",
  subscribe: "/api/wallet/subscribe",
  vitcoinPrice: "/api/wallet/vitcoin-price",
};

export const getGetMeQueryKey = () => [API.me];
export const getGetDashboardSummaryQueryKey = () => [API.dashboard.summary];
export const getGetVitcoinPriceQueryKey = () => [API.dashboard.vitcoinPrice];
export const getGetRecentActivityQueryKey = () => [API.dashboard.recentActivity];
export const getListMatchesQueryKey = (params?: Record<string, unknown>) => [API.matches, params];
export const getGetMatchQueryKey = (id: string) => [API.match(id)];
export const getListPredictionsQueryKey = () => [API.predictions];
export const getListTrainingJobsQueryKey = () => [API.training.jobs];
export const getGetModelPerformanceQueryKey = () => [API.training.modelPerformance];
export const getListValidatorsQueryKey = () => [API.validators];
export const getGetEconomyQueryKey = () => [API.economy];
export const getGetWalletQueryKey = () => [API.wallet];
export const getListTransactionsQueryKey = () => [API.transactions];
export const getGetMyStakesQueryKey = () => [API.myStakes];
export const getGetMyValidatorQueryKey = () => [API.myValidator];
export const getConsensusPredictionQueryKey = (matchId: string) => [API.consensusPrediction(matchId)];

export function useGetMe(opts?: { query?: { enabled?: boolean; retry?: boolean } }) {
  return useQuery<User>({
    queryKey: getGetMeQueryKey(),
    queryFn: () => apiGet<User>(API.me),
    enabled: opts?.query?.enabled ?? true,
    retry: opts?.query?.retry ?? true,
  });
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: number;
  username: string;
  role: string;
}

export function useLogin() {
  return useMutation<AuthResponse, Error, { data: { email: string; password: string } }>({
    mutationFn: ({ data }) => apiPost<AuthResponse>(API.login, data),
  });
}

export function useRegister() {
  return useMutation<AuthResponse, Error, { data: { username: string; email: string; password: string; referral_code?: string } }>({
    mutationFn: ({ data }) => apiPost<AuthResponse>(API.register, data),
  });
}

export function useGetDashboardSummary() {
  return useQuery<DashboardSummary>({
    queryKey: getGetDashboardSummaryQueryKey(),
    queryFn: () => apiGet<DashboardSummary>(API.dashboard.summary),
  });
}

export function useGetVitcoinPrice() {
  return useQuery<{ price: number; change_24h: number }>({
    queryKey: getGetVitcoinPriceQueryKey(),
    queryFn: () => apiGet<{ price: number; change_24h: number }>(API.dashboard.vitcoinPrice),
  });
}

export function useGetRecentActivity() {
  return useQuery<any[]>({
    queryKey: getGetRecentActivityQueryKey(),
    queryFn: () => apiGet<any[]>(API.dashboard.recentActivity),
  });
}

export function useListMatches(params?: Record<string, unknown>) {
  return useQuery<{ matches: Match[]; count: number }>({
    queryKey: getListMatchesQueryKey(params),
    queryFn: async () => {
      const qs = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "";
      const data = await apiGet<{ matches: Match[]; count: number }>(API.matches + qs);
      return data;
    },
    staleTime: 60_000,
  });
}

export function useSyncFixtures() {
  const queryClient = useQueryClient();
  return useMutation<{ stored: number; skipped_existing: number; source: string; message: string }, Error, { days?: number }>({
    mutationFn: ({ days = 14 } = {}) =>
      apiPost<any>(`/matches/sync?days=${days}`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [API.matches] });
      queryClient.invalidateQueries({ queryKey: ["matches-recent"] });
    },
  });
}

export function useListLeagues() {
  return useQuery<{ leagues: { key: string; display: string }[] }>({
    queryKey: ["matches-leagues"],
    queryFn: () => apiGet<{ leagues: { key: string; display: string }[] }>("/matches/leagues/list"),
    staleTime: 5 * 60_000,
  });
}

export function useListMatchesExplore(params?: Record<string, unknown>) {
  return useQuery<{ matches: Match[]; count: number }>({
    queryKey: ["matches-explore", params],
    queryFn: async () => {
      const qs = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "";
      return apiGet<{ matches: Match[]; count: number }>(API.matchesExplore + qs);
    },
  });
}

export function useListRecentMatches() {
  return useQuery<{ matches: Match[]; count: number }>({
    queryKey: ["matches-recent"],
    queryFn: () => apiGet<{ matches: Match[]; count: number }>(API.matchesRecent),
  });
}

export function useGetMyAnalytics() {
  return useQuery<any>({
    queryKey: ["analytics-my"],
    queryFn: () => apiGet<any>(API.analyticsMyStats),
  });
}

export function useGetMatch(id: string) {
  return useQuery<Match>({
    queryKey: getGetMatchQueryKey(id),
    queryFn: async () => {
      const raw = await apiGet<any>(API.match(id));
      // New /matches/{id} format: { match: {...}, predictions: [...] }
      if (raw && raw.match) {
        const m = raw.match;
        const pred = raw.predictions?.[0] ?? null;
        return {
          match_id: m.match_id ?? m.id,
          home_team: m.home_team,
          away_team: m.away_team,
          league: m.league,
          kickoff_time: m.kickoff_time,
          ft_score: m.ft_score ?? null,
          actual_outcome: m.actual_outcome,
          status: m.status,
          home_goals: m.home_goals,
          away_goals: m.away_goals,
          odds: m.odds,
          home_prob: pred?.home_prob ?? m.home_prob ?? null,
          draw_prob: pred?.draw_prob ?? m.draw_prob ?? null,
          away_prob: pred?.away_prob ?? m.away_prob ?? null,
          over_25_prob: pred?.over_25_prob ?? m.over_25_prob ?? null,
          under_25_prob: pred?.under_25_prob ?? m.under_25_prob ?? null,
          over_15_prob: m.over_15_prob ?? null,
          over_35_prob: m.over_35_prob ?? null,
          btts_prob: pred?.btts_prob ?? m.btts_prob ?? null,
          no_btts_prob: pred?.no_btts_prob ?? m.no_btts_prob ?? null,
          consensus_prob: pred?.consensus_prob ?? m.consensus_prob ?? null,
          recommended_stake: pred?.recommended_stake ?? m.recommended_stake ?? null,
          final_ev: pred?.final_ev ?? null,
          edge: pred?.edge ?? m.edge ?? null,
          confidence: pred?.confidence ?? m.confidence ?? null,
          bet_side: pred?.bet_side ?? m.bet_side ?? null,
          entry_odds: pred?.entry_odds ?? m.entry_odds ?? null,
          clv: null,
          profit: null,
          timestamp: pred?.timestamp ?? m.kickoff_time,
          predictions_count: raw.predictions_count,
          _all_predictions: raw.predictions,
          // Pass through extra rich data for extended display
          _markets: raw.markets,
          enabled_markets: raw.enabled_markets ?? m.enabled_markets,
          model_contributions: raw.model_contributions ?? [],
          consensus_breakdown: raw.consensus_breakdown,
          recent_form: raw.recent_form,
          head_to_head: raw.head_to_head,
          _model_summary: raw.model_summary,
          _neural_info: raw.neural_info,
        } as Match & { _markets?: any; _model_summary?: any; _neural_info?: any };
      }
      return raw as Match;
    },
    enabled: !!id,
  });
}

export function useCreatePrediction() {
  const queryClient = useQueryClient();
  return useMutation<Prediction, Error, { data: Record<string, unknown> }>({
    mutationFn: ({ data }) => apiPost<Prediction>("/predict", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getListPredictionsQueryKey() });
    },
  });
}

export function useListPredictions(params?: { all_users?: boolean; limit?: number }) {
  const qs = new URLSearchParams();
  if (params?.all_users) qs.set("all_users", "true");
  if (params?.limit) qs.set("limit", String(params.limit));
  const query = qs.toString();
  const url = query ? `${API.predictions}?${query}` : API.predictions;
  return useQuery<{ predictions: Prediction[]; total: number; scope?: string }>({
    queryKey: [API.predictions, params ?? {}],
    queryFn: () => apiGet<{ predictions: Prediction[]; total: number; scope?: string }>(url),
  });
}

// ─── Ticket Builder (v4.12.0) ───────────────────────────────────────────
export interface TicketMarket {
  key: string;
  label: string;
  category: string;
  uses_real_odds: boolean;
}

export interface TicketCandidate {
  match_id: number;
  home_team: string;
  away_team: string;
  league: string;
  kickoff_time: string | null;
  market: string;
  market_label: string;
  selection: string;
  probability: number;
  odds: number;
  odds_source: "bookmaker_opening" | "model_fair";
  edge: number;
  confidence: number;
  ev_score: number;
}

export interface BuiltTicket {
  n_legs: number;
  legs: TicketCandidate[];
  combined_prob: number;
  combined_odds: number;
  fair_odds: number;
  combined_edge: number;
  correlation_penalty: number;
  adjusted_edge: number;
  avg_confidence: number;
  kelly_stake: number;
  potential_return_per_unit: number;
}

export function useGetTicketMarkets() {
  return useQuery<{ markets: TicketMarket[]; unsupported: { key: string; reason: string }[] }>({
    queryKey: [API.ticketMarkets],
    queryFn: () => apiGet(API.ticketMarkets),
    staleTime: 5 * 60 * 1000,
  });
}

export function useGetTicketCandidates(params: {
  market: string;
  min_confidence?: number;
  min_edge?: number;
  limit?: number;
  only_upcoming?: boolean;
  enabled?: boolean;
}) {
  const qs = new URLSearchParams();
  qs.set("market", params.market);
  if (params.min_confidence != null) qs.set("min_confidence", String(params.min_confidence));
  if (params.min_edge != null) qs.set("min_edge", String(params.min_edge));
  if (params.limit != null) qs.set("limit", String(params.limit));
  if (params.only_upcoming != null) qs.set("only_upcoming", String(params.only_upcoming));
  return useQuery<{
    market: string;
    market_label: string;
    total_found: number;
    candidates: TicketCandidate[];
  }>({
    queryKey: [API.ticketCandidates, params],
    queryFn: () => apiGet(`${API.ticketCandidates}?${qs.toString()}`),
    enabled: params.enabled !== false && !!params.market,
  });
}

export function useBuildTicket() {
  return useMutation<
    { requested_legs: number; total_generated: number; tickets: BuiltTicket[] },
    Error,
    {
      candidates: TicketCandidate[];
      legs: number;
      top_n?: number;
      min_combined_edge?: number;
      same_match_allowed?: boolean;
    }
  >({
    mutationFn: (body) => apiPost(API.ticketBuild, body),
  });
}

export function useListTrainingJobs() {
  return useQuery<{ jobs: TrainingJob[]; total: number }>({
    queryKey: getListTrainingJobsQueryKey(),
    queryFn: () => apiGet<{ jobs: TrainingJob[]; total: number }>(API.training.jobs),
  });
}

export function useGetModelPerformance() {
  return useQuery<any>({
    queryKey: getGetModelPerformanceQueryKey(),
    queryFn: async () => {
      const raw = await apiGet<any>(API.training.modelPerformance);
      // Backend (`/api/dashboard/model-confidence`) returns accuracy as a 0–100
      // percentage, but the chart and gauge expect a 0–1 fraction. Normalize
      // here so consumers don't have to know the unit.
      const models = (raw?.models ?? []).map((m: any) => ({
        ...m,
        accuracy: typeof m.accuracy === "number" ? m.accuracy / 100 : 0,
      }));
      const ensemble = typeof raw?.ensemble_accuracy === "number" ? raw.ensemble_accuracy / 100 : 0;
      return {
        ...raw,
        models,
        ensemble_accuracy: ensemble,
        accuracy_rate: ensemble,
      };
    },
  });
}

export function useUploadTrainingData() {
  const queryClient = useQueryClient();
  return useMutation<any, Error, FormData>({
    mutationFn: (formData: FormData) =>
      fetch(API.training.upload, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("vit_token")}` },
        body: formData,
      }).then((r) => {
        if (!r.ok) throw new Error("Upload failed");
        return r.json();
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: getListTrainingJobsQueryKey() }),
  });
}

export function useListValidators() {
  return useQuery<Validator[]>({
    queryKey: getListValidatorsQueryKey(),
    queryFn: () => apiGet<Validator[]>(API.validators),
  });
}

export function useGetEconomy() {
  return useQuery<any>({
    queryKey: getGetEconomyQueryKey(),
    queryFn: () => apiGet<any>(API.economy),
  });
}

export function useGetMyValidator() {
  return useQuery<any>({
    queryKey: getGetMyValidatorQueryKey(),
    queryFn: () => apiGet<any>(API.myValidator),
    retry: false,
  });
}

export function useApplyAsValidator() {
  const queryClient = useQueryClient();
  return useMutation<any, Error, { stake_amount: number }>({
    mutationFn: (data) => apiPost<any>(API.applyValidator, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getListValidatorsQueryKey() });
      queryClient.invalidateQueries({ queryKey: getGetMyValidatorQueryKey() });
    },
  });
}

export function useStakeOnPrediction() {
  const queryClient = useQueryClient();
  return useMutation<any, Error, { matchId: string; prediction: string; amount: number }>({
    mutationFn: ({ matchId, prediction, amount }) =>
      apiPost<any>(API.stake(matchId), { prediction, amount }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getGetMyStakesQueryKey() });
      queryClient.invalidateQueries({ queryKey: getGetWalletQueryKey() });
    },
  });
}

export function useGetMyStakes() {
  return useQuery<any[]>({
    queryKey: getGetMyStakesQueryKey(),
    queryFn: () => apiGet<any[]>(API.myStakes),
  });
}

export function useGetConsensusPrediction(matchId: string) {
  return useQuery<any>({
    queryKey: getConsensusPredictionQueryKey(matchId),
    queryFn: () => apiGet<any>(API.consensusPrediction(matchId)),
    enabled: !!matchId,
    retry: false,
  });
}

export function useGetWallet() {
  return useQuery<Wallet>({
    queryKey: getGetWalletQueryKey(),
    queryFn: () => apiGet<Wallet>(API.wallet),
  });
}

export function useListTransactions(params?: { currency?: string; limit?: number }) {
  return useQuery<{ transactions: Transaction[]; total: number }>({
    queryKey: [API.transactions, params],
    queryFn: () => {
      const qs = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "";
      return apiGet<{ transactions: Transaction[]; total: number }>(API.transactions + qs);
    },
  });
}

export function useInitiateDeposit() {
  const queryClient = useQueryClient();
  return useMutation<{ payment_link: string; reference: string; status: string; amount: number; currency: string; method: string }, Error, { currency: string; amount: number; method: string }>({
    mutationFn: (data) => apiPost<{ payment_link: string; reference: string; status: string; amount: number; currency: string; method: string }>(API.depositInitiate, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [API.transactions] }),
  });
}

export function useVerifyDeposit() {
  const queryClient = useQueryClient();
  return useMutation<any, Error, { reference: string; currency: string }>({
    mutationFn: (data) => apiPost<any>(API.depositVerify, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: getGetWalletQueryKey() }),
  });
}

export function useConvertCurrency() {
  const queryClient = useQueryClient();
  return useMutation<any, Error, { from_currency: string; to_currency: string; amount: number }>({
    mutationFn: (data) => apiPost<any>(API.convert, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getGetWalletQueryKey() });
      queryClient.invalidateQueries({ queryKey: [API.transactions] });
    },
  });
}

export function useWithdraw() {
  const queryClient = useQueryClient();
  return useMutation<any, Error, { currency: string; amount: number; destination: string; destination_type: string }>({
    mutationFn: (data) => apiPost<any>(API.withdraw, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: getGetWalletQueryKey() }),
  });
}

export interface TopOpportunity {
  match: string;
  league: string;
  edge: string;
  edge_value: number;
  ai_confidence: number;
  time: string;
  bet_side: string;
  prediction_id: string;
  match_id: string;
}

export interface ModelConfidence {
  name: string;
  key: string;
  accuracy: number;
  weight: number;
  predictions: number;
  status: string;
}

export function useGetTopOpportunities(limit = 5) {
  return useQuery<{ opportunities: TopOpportunity[]; total: number }>({
    queryKey: ["dashboard-top-opportunities", limit],
    queryFn: () => apiGet<{ opportunities: TopOpportunity[]; total: number }>(
      `/api/dashboard/top-opportunities?limit=${limit}`
    ),
    refetchInterval: 60_000,
    retry: 1,
  });
}

export function useGetModelConfidence() {
  return useQuery<{ models: ModelConfidence[]; ensemble_accuracy: number; active_count: number }>({
    queryKey: ["dashboard-model-confidence"],
    queryFn: () => apiGet<{ models: ModelConfidence[]; ensemble_accuracy: number; active_count: number }>(
      "/api/dashboard/model-confidence"
    ),
    refetchInterval: 120_000,
    retry: 1,
  });
}

export function useAdminFetchFixtures() {
  const queryClient = useQueryClient();
  return useMutation<{ stored: number; skipped_existing: number; errors: number; message: string }, Error, { days?: number; count?: number }>({
    mutationFn: ({ days = 7, count = 50 } = {}) =>
      apiPost<any>(`/admin/matches/fetch-fixtures?days=${days}&count=${count}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getListMatchesQueryKey() });
      queryClient.invalidateQueries({ queryKey: ["matches-explore"] });
      queryClient.invalidateQueries({ queryKey: ["matches-recent"] });
    },
  });
}

export function useAdminFetchLive() {
  const queryClient = useQueryClient();
  return useMutation<{ live_count: number; db_updated: number }, Error, void>({
    mutationFn: () => apiPost<any>("/admin/matches/fetch-live"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getListMatchesQueryKey() });
    },
  });
}
