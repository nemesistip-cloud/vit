import { useQuery } from '@tanstack/react-query'
import { storageApi } from '@/lib/api'

export function useStorageList() {
  return useQuery({
    queryKey: ['storage', 'list'],
    queryFn: ({ signal }) => storageApi.list(signal),
    staleTime: 15_000,
  })
}

export function useStorageMetrics() {
  return useQuery({
    queryKey: ['storage', 'metrics'],
    queryFn: ({ signal }) => storageApi.metrics(signal),
    refetchInterval: 60_000,
  })
}
