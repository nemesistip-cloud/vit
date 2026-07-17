import { useQuery } from '@tanstack/react-query'
import { gatewayApi, aiApi, storageApi } from '@/lib/api'

export function useGatewayHealth() {
  return useQuery({
    queryKey: ['health', 'gateway'],
    queryFn: ({ signal }) => gatewayApi.health(signal),
    refetchInterval: 30_000,
  })
}

export function useAIHealth() {
  return useQuery({
    queryKey: ['health', 'ai'],
    queryFn: ({ signal }) => aiApi.health(signal),
    refetchInterval: 30_000,
  })
}

export function useStorageHealth() {
  return useQuery({
    queryKey: ['health', 'storage'],
    queryFn: ({ signal }) => storageApi.health(signal),
    refetchInterval: 30_000,
  })
}

export function useAllHealth() {
  const gateway = useGatewayHealth()
  const ai      = useAIHealth()
  const storage = useStorageHealth()

  const isLoading = gateway.isLoading || ai.isLoading || storage.isLoading
  const isError   = gateway.isError   || ai.isError   || storage.isError

  const overallStatus = (() => {
    if (isLoading) return 'loading'
    if (
      gateway.data?.status?.toLowerCase() === 'healthy' &&
      ai.data?.status?.toLowerCase() === 'healthy' &&
      storage.data?.status?.toLowerCase() === 'healthy'
    ) return 'healthy'
    if (isError) return 'unhealthy'
    return 'degraded'
  })()

  return { gateway, ai, storage, isLoading, isError, overallStatus }
}
