import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./apiClient";

export interface CurrencyMeta {
  code: string;
  symbol: string;
  label: string;
  decimals: number;
}

export interface LeagueMeta {
  id: string;
  raw: string;
  label: string;
  short: string;
}

export interface PublicConfig {
  currencies: CurrencyMeta[];
  deposit_presets: Record<string, number[]>;
  leagues: LeagueMeta[];
  league_short: Record<string, string>;
  bookmaker_labels: Record<string, string>;
  plan_order: string[];
  plan_feature_labels: Record<string, string>;
  governance_categories: { id: string; label: string }[];
  fx: {
    ngn_usd_rate: number;
    ngn_per_usd: number;
    pi_usd_rate: number;
    vit_usd: number;
  };
  platform: {
    welcome_bonus_vit: number;
    model_count: number;
    version: string;
  };
}

/** Fetches the public configuration (currencies, leagues, fx rates, plan order, etc.).
 *  Cached for 5 minutes on the client; cached for 60s server-side.
 *  Returns undefined while loading — UIs should render a skeleton, not invented data. */
export function usePublicConfig() {
  return useQuery<PublicConfig>({
    queryKey: ["public-config"],
    queryFn: () => apiGet<PublicConfig>("/config/public"),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
}

export function useCurrencyCodes(): string[] | undefined {
  const { data } = usePublicConfig();
  return data?.currencies.map((c) => c.code);
}
