import { useQuery } from '@tanstack/react-query'
import { storageApi } from '@/lib/api'

// Verified endpoint: GET /api/v1/files (returns StorageFile[])
export function useStorageFiles() {
  return useQuery({
    queryKey: ['storage', 'files'],
    queryFn: ({ signal }) => storageApi.files(signal),
    staleTime: 15_000,
    retry: 1,
  })
}

// Alias kept for backward compat
export const useStorageList = useStorageFiles

// GET /api/v1/status — tachyon coordination plane metrics
export function useTachyonStatus() {
  return useQuery({
    queryKey: ['storage', 'tachyon-status'],
    queryFn: ({ signal }) => storageApi.tachyonStatus(signal),
    refetchInterval: 30_000,
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
