import { useQuery } from '@tanstack/react-query'
import { gatewayApi, aiApi, storageApi, chainApi } from '@/lib/api'

export function useGatewayHealth() {
  return useQuery({
    queryKey: ['health', 'gateway'],
    queryFn: ({ signal }) => gatewayApi.health(signal),
    refetchInterval: 30_000,
    retry: 1,
  })
}

export function useAIHealth() {
  return useQuery({
    queryKey: ['health', 'ai'],
    queryFn: ({ signal }) => aiApi.health(signal),
    refetchInterval: 30_000,
    retry: 1,
  })
}

export function useStorageHealth() {
  return useQuery({
    queryKey: ['health', 'storage'],
    queryFn: ({ signal }) => storageApi.health(signal),
    refetchInterval: 30_000,
    retry: 1,
  })
}

export function useChainHealth() {
  return useQuery({
    queryKey: ['health', 'chain'],
    queryFn: ({ signal }) => chainApi.ping(signal),
    refetchInterval: 30_000,
    retry: 1,
  })
}

export function useAllHealth() {
  const gateway = useGatewayHealth()
  const ai      = useAIHealth()
  const storage = useStorageHealth()
  const chain   = useChainHealth()

  const isLoading = gateway.isLoading || ai.isLoading || storage.isLoading || chain.isLoading
  const isError   = gateway.isError   || ai.isError   || storage.isError   || chain.isError

  const statuses = [
    gateway.data?.status?.toLowerCase(),
    ai.data?.status?.toLowerCase(),
    storage.data?.status?.toLowerCase(),
    chain.data?.status?.toLowerCase(),
  ]

  const overallStatus = (() => {
    if (isLoading) return 'loading'
    const healthy = ['healthy', 'ok', 'quantum_stable']
    if (statuses.every(s => s && healthy.includes(s))) return 'healthy'
    if (isError) return 'unhealthy'
    return 'degraded'
  })()

  return { gateway, ai, storage, chain, isLoading, isError, overallStatus }
}
