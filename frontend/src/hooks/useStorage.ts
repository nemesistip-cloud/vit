import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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

export function useStorageUpload() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => storageApi.upload(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['storage', 'list'] })
      qc.invalidateQueries({ queryKey: ['health', 'storage'] })
    },
  })
}

export function useStorageDelete() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (key: string) => storageApi.delete(key),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['storage', 'list'] })
      qc.invalidateQueries({ queryKey: ['health', 'storage'] })
    },
  })
}
