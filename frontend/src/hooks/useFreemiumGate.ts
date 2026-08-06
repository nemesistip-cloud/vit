import { useQuery } from '@tanstack/react-query'
import { ENDPOINTS } from '@/lib/api'

interface PublicConfig {
  predictions_enabled?: boolean
  wallet_enabled?: boolean
  governance_enabled?: boolean
  marketplace_enabled?: boolean
  defi_enabled?: boolean
  social_enabled?: boolean
  inplay_enabled?: boolean
  analytics_enabled?: boolean
  enterprise_enabled?: boolean
  max_free_predictions?: number
  [key: string]: boolean | number | string | undefined
}

function usePublicConfig() {
  return useQuery<PublicConfig>({
    queryKey: ['public-config'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/config/public`, { signal })
      if (!r.ok) throw new Error(`Config API returned ${r.status}`)
      return r.json()
    },
    staleTime: 5 * 60_000,
    retry: 1,
  })
}

/**
 * Returns whether a feature is enabled by the platform config.
 *
 * Phase 6 rule: "Missing configuration must never disable the application."
 * - While loading → enabled: true  (optimistic unlock — don't block UI)
 * - Config API error → enabled: true  (fail-open — don't disable on network failure)
 * - Key absent from config → enabled: true  (missing ≠ explicitly disabled)
 * - Key explicitly set to false → enabled: false  (only hard-coded denial takes effect)
 *
 * @example
 * const { enabled, loading } = useFeatureGate('predictions_enabled')
 * if (!enabled) return <UpgradePrompt />
 */
export function useFeatureGate(feature: keyof PublicConfig): { enabled: boolean; loading: boolean } {
  const { data, isLoading, isError } = usePublicConfig()

  // Optimistic unlock while the config is in flight.
  if (isLoading) return { enabled: true, loading: true }

  // Config unavailable → fail-open (never disable the app due to an API outage).
  if (isError || !data) return { enabled: true, loading: false }

  const val = data[feature]

  // Key absent → treat as enabled (missing flag ≠ disabled feature).
  if (val === undefined) return { enabled: true, loading: false }

  // Only a hard false disables the feature.
  return { enabled: Boolean(val), loading: false }
}
