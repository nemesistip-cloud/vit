import { useQuery } from '@tanstack/react-query'
import { gatewayApi, aiApi, storageApi } from '@/lib/api'

const HEALTHY_STATUSES = new Set(['healthy', 'quantum_stable', 'operational', 'ok', 'up'])

function isHealthy(status?: string) {
  return status ? HEALTHY_STATUSES.has(status.toLowerCase()) : false
}

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
    const gwOk  = gateway.data ? (isHealthy(gateway.data.status) || gateway.data.status === 'degraded') : !gateway.isError
    const aiOk  = ai.data      ? isHealthy(ai.data.status) : !ai.isError
    const stOk  = storage.data ? isHealthy(storage.data.status) : !storage.isError
    if (isError && !(gwOk && aiOk && stOk)) return 'unhealthy'
    if (
      isHealthy(gateway.data?.status) &&
      isHealthy(ai.data?.status) &&
      isHealthy(storage.data?.status)
    ) return 'healthy'
    return 'degraded'
  })()

  return { gateway, ai, storage, isLoading, isError, overallStatus }
}
