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

// Returns string[] e.g. ["internal", "ensemble"]
export function useAIProviders() {
  return useQuery({
    queryKey: ['ai', 'providers'],
    queryFn: ({ signal }) => aiApi.providers(signal),
    refetchInterval: 30_000,
  })
}

export function useEnsembleStatus() {
  return useQuery({
    queryKey: ['ai', 'ensemble-status'],
    queryFn: ({ signal }) => aiApi.ensembleStatus(signal),
    refetchInterval: 30_000,
    retry: 1,
  })
}

export function useAIDatasets() {
  return useQuery({
    queryKey: ['ai', 'datasets'],
    queryFn: ({ signal }) => aiApi.datasets(signal),
    staleTime: 60_000,
    retry: 1,
  })
}

export function useAIVersion() {
  return useQuery({
    queryKey: ['ai', 'version'],
    queryFn: ({ signal }) => aiApi.version(signal),
    staleTime: 300_000,
  })
}
