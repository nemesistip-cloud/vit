import { useQuery } from '@tanstack/react-query'
import { aiApi } from '@/lib/api'

export function useAIModels() {
  return useQuery({
    queryKey: ['ai', 'models'],
    queryFn: ({ signal }) => aiApi.models(signal),
    staleTime: 60_000,
  })
}

export function useAIKernelStatus() {
  return useQuery({
    queryKey: ['ai', 'kernel-status'],
    queryFn: ({ signal }) => aiApi.aiStatus(signal),
    refetchInterval: 30_000,
  })
}

export function useAIProviders() {
  return useQuery({
    queryKey: ['ai', 'providers'],
    queryFn: ({ signal }) => aiApi.providers(signal),
    refetchInterval: 30_000,
  })
}

export function useAIFeatures() {
  return useQuery({
    queryKey: ['ai', 'features'],
    queryFn: ({ signal }) => aiApi.features(signal),
    staleTime: 120_000,
  })
}

export function useAIVersion() {
  return useQuery({
    queryKey: ['ai', 'version'],
    queryFn: ({ signal }) => aiApi.version(signal),
    staleTime: 300_000,
  })
}
