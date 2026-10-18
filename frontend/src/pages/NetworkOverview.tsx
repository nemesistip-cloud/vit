import { useQuery } from '@tanstack/react-query'
import { Activity, ArrowRight, Boxes, CircleAlert, ExternalLink, Shield } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'

interface RegistryResponse {
  status?: string
  version?: string
  services?: Record<string, { status?: string; version?: string; latency_ms?: number }>
}

export default function NetworkOverview() {
  const registry = useQuery<RegistryResponse>({
    queryKey: ['network-service-registry'],
    queryFn: async ({ signal }) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/registry`, { signal })
      if (!response.ok) throw new Error(`Network status unavailable (${response.status})`)
      return response.json()
    },
    retry: 1,
    staleTime: 30_000,
  })

  const services = registry.data?.services ?? {}

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase text-emerald-300/75">VIT Network</p>
          <h1 className="text-3xl font-semibold">Network overview</h1>
          <p className="mt-2 text-sm text-white/55">Shared infrastructure, network health, and applications.</p>
        </div>
        <Link to="/applications" className="inline-flex items-center gap-2 rounded-md bg-emerald-300 px-3 py-2 text-sm font-semibold text-[#092018] hover:bg-emerald-200">Browse applications <ArrowRight className="h-4 w-4" /></Link>
      </header>

      <section aria-labelledby="network-health-title">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 id="network-health-title" className="flex items-center gap-2 text-base font-semibold"><Activity className="h-4 w-4 text-emerald-300" /> Shared service health</h2>
          {registry.data?.version && <span className="text-xs text-white/35">Gateway v{registry.data.version}</span>}
        </div>
        {registry.isPending ? <div className="flex min-h-28 items-center justify-center"><Spinner className="h-5 w-5 text-emerald-300" /></div> : registry.isError ? (
          <div role="alert" className="flex items-start gap-3 border-l-2 border-amber-400 bg-amber-400/5 px-4 py-3 text-sm"><CircleAlert className="mt-0.5 h-4 w-4 text-amber-300" /><div><p>Network health could not be loaded.</p><p className="mt-1 text-xs text-white/45">{registry.error.message}</p></div></div>
        ) : (
          <ul className="grid gap-px overflow-hidden rounded-lg border border-white/10 bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(services).map(([name, service]) => {
              const healthy = ['ok', 'healthy', 'starting', 'quantum_stable'].includes((service.status ?? '').toLowerCase())
              return <li key={name} className="bg-[#101922] px-4 py-4"><div className="flex items-center justify-between gap-3"><span className="font-medium capitalize">{name}</span><span className={`h-2 w-2 rounded-full ${healthy ? 'bg-emerald-300' : 'bg-amber-300'}`} /></div><p className={`mt-2 text-xs capitalize ${healthy ? 'text-emerald-200/80' : 'text-amber-200/80'}`}>{service.status ?? 'unknown'}</p>{service.latency_ms != null && <p className="mt-1 text-[11px] text-white/35">{service.latency_ms} ms</p>}</li>
            })}
          </ul>
        )}
      </section>

      <section aria-labelledby="network-services-title">
        <h2 id="network-services-title" className="mb-3 text-base font-semibold">Network services</h2>
        <div className="divide-y divide-white/10 border-y border-white/10">
          <Link to="/chain" className="group flex items-center gap-4 py-4"><span className="flex h-9 w-9 items-center justify-center rounded-md border border-cyan-300/20 text-cyan-200"><Shield className="h-4 w-4" /></span><span className="flex-1"><span className="block text-sm font-medium">Chain explorer</span><span className="mt-1 block text-xs text-white/45">Blocks, transactions, validators, and network activity.</span></span><ExternalLink className="h-4 w-4 text-white/35 group-hover:text-white" /></Link>
          <Link to="/applications" className="group flex items-center gap-4 py-4"><span className="flex h-9 w-9 items-center justify-center rounded-md border border-emerald-300/20 text-emerald-200"><Boxes className="h-4 w-4" /></span><span className="flex-1"><span className="block text-sm font-medium">Application directory</span><span className="mt-1 block text-xs text-white/45">Discover independent products connected to VIT Network.</span></span><ExternalLink className="h-4 w-4 text-white/35 group-hover:text-white" /></Link>
        </div>
      </section>
    </div>
  )
}