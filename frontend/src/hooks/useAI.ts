import { useQuery } from '@tanstack/react-query'
import { aiApi } from '@/lib/api'

export function useAIModels() {
  return useQuery({
    queryKey: ['ai', 'models'],
    queryFn: ({ signal }) => aiApi.models(signal),
    staleTime: 60_000,
  })
}

export function useAIStatus() {
  return useQuery({
    queryKey: ['ai', 'status'],
    queryFn: ({ signal }) => aiApi.status(signal),
    refetchInterval: 30_000,
  })
}
