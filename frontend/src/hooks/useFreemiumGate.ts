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
      return r.ok ? r.json() : {}
    },
    staleTime: 5 * 60_000,
    retry: false,
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
  const { data, isLoading } = usePublicConfig()

  if (isLoading) return { enabled: true, loading: true }

  const val = data?.[feature]
  // If undefined (key not returned by API) treat as enabled
  const enabled = val === undefined ? true : Boolean(val)

  return { enabled, loading: false }
}
