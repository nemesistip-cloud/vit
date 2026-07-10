import { useQuery } from '@tanstack/react-query'
import { storageApi } from '@/lib/api'

export function useStorageList() {
  return useQuery({
    queryKey: ['storage', 'list'],
    queryFn: async ({ signal }) => {
      // Try primary tachyon manifests endpoint, fallback to legacy
      try {
        return await storageApi.list(signal)
      } catch {
        return storageApi.listAlt(signal)
      }
    },
    staleTime: 15_000,
    retry: 1,
  })
}

export function useTachyonStatus() {
  return useQuery({
    queryKey: ['storage', 'tachyon-status'],
    queryFn: ({ signal }) => storageApi.tachyonStatus(signal),
    refetchInterval: 30_000,
    retry: 1,
  })
}

export function useStorageMetrics() {
  return useQuery({
    queryKey: ['storage', 'metrics'],
    queryFn: ({ signal }) => storageApi.metrics(signal),
    refetchInterval: 60_000,
    retry: 1,
  })
}
