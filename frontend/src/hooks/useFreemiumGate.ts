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
 * Defaults to `true` if the config hasn't loaded yet (optimistic unlock).
 *
 * @example
 * const { enabled, loading } = useFeatureGate('predictions_enabled')
 * if (!enabled) return <UpgradePrompt />
 */
export function useFeatureGate(feature: keyof PublicConfig): { enabled: boolean; loading: boolean } {
  // H5 fix: fail-closed — when config is loading or errored, gate features OFF.
  const { data, isLoading, isError } = usePublicConfig()

  if (isLoading) return { enabled: false, loading: true }

  // Config API failure → deny access (fail-closed)
  if (isError || !data) return { enabled: false, loading: false }

  const val = data[feature]
  // If key is absent from the config payload, default to disabled (fail-closed)
  const enabled = val === undefined ? false : Boolean(val)

  return { enabled, loading: false }
}
