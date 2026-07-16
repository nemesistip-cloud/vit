import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { Activity, Database, Brain, HardDrive, Server, Wifi, RefreshCw, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'

function useGatewayObs() {
  return useQuery({
    queryKey: ['obs-health'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/obs/health`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 15_000, refetchInterval: 30_000,
  })
}

function useSystemSummary() {
  return useQuery({
    queryKey: ['system-summary'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/system/health/summary`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 15_000, refetchInterval: 30_000,
  })
}

function useAiHealth() {
  return useQuery({
    queryKey: ['ai-health-status'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/ai-feed/health`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 20_000, refetchInterval: 30_000,
  })
}

function useStorageHealth() {
  return useQuery({
    queryKey: ['storage-health-status'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/storage/health`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 20_000, refetchInterval: 30_000,
  })
}

function useGatewayPing() {
  return useQuery({
    queryKey: ['gateway-ping'],
    queryFn: async ({ signal }) => {
      const start = performance.now()
      const r = await fetch(`${ENDPOINTS.gateway}/ping`, { signal })
      const latency = Math.round(performance.now() - start)
      return r.ok ? { status: 'ok', latency } : null
    },
    staleTime: 15_000, refetchInterval: 30_000,
  })
}

function ServiceCard({ icon: Icon, label, status, details, isLoading }: {
  icon: React.ElementType
  label: string
  status?: string
  details?: { label: string; value?: string | number | null }[]
  isLoading?: boolean
}) {
  const s = status?.toLowerCase()
  const isOk  = s === 'healthy' || s === 'ok' || s === 'operational' || s === 'active'
  const isDeg = s === 'degraded' || s === 'warning' || s === 'partial'
  const isErr = s === 'unhealthy' || s === 'error' || s === 'down' || s === 'failed'

  const StatusIcon = isOk ? CheckCircle : isDeg ? AlertTriangle : isErr ? XCircle : null

  return (
    <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
            <Icon className="w-5 h-5 text-vit-400" />
          </div>
          <span className="font-semibold text-white">{label}</span>
        </div>
        {isLoading ? <Spinner className="w-4 h-4" /> : (
          <div className="flex items-center gap-2">
            <StatusBadge status={status} size="sm" pulse={isOk} />
          </div>
        )}
      </div>
      {details && details.length > 0 && (
        <div className="space-y-2 pt-3 border-t border-white/6">
          {details.filter(d => d.value != null).map(d => (
            <div key={d.label} className="flex items-center justify-between text-xs">
              <span className="text-white/40">{d.label}</span>
              <span className="text-white/70 font-medium">{d.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function SubsystemRow({ name, status, message }: { name: string; status: string; message?: string }) {
  const isOk  = status?.toLowerCase() === 'healthy'
  const isDeg = status?.toLowerCase() === 'degraded'
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-white/5 last:border-0">
      <span className={cn('w-2 h-2 rounded-full shrink-0',
        isOk ? 'bg-emerald-400' : isDeg ? 'bg-amber-400' : 'bg-red-400',
        isOk && 'animate-pulse'
      )} />
      <span className="text-sm text-white capitalize">{name}</span>
      <span className="ml-auto text-xs text-white/30 capitalize">{status}</span>
      {message && <span className="text-xs text-white/25 hidden sm:block max-w-[200px] truncate">{message}</span>}
    </div>
  )
}

export default function Status() {
  const { data: obs,     isLoading: obsLoading }     = useGatewayObs()
  const { data: summary, isLoading: summaryLoading } = useSystemSummary()
  const { data: ai,      isLoading: aiLoading }      = useAiHealth()
  const { data: ping,    isLoading: pingLoading, refetch }   = useGatewayPing()

  const overallStatus = summary?.overall_status ?? obs?.status ?? (obsLoading ? 'loading' : 'unknown')
  const details       = summary?.details ?? {}

  const services = [
    {
      icon: Server,
      label: 'VIT Gateway',
      status: overallStatus === 'loading' ? undefined : details.kernel ?? details.platform ?? overallStatus,
      isLoading: summaryLoading,
      details: [
        { label: 'Version',  value: '1.1.0' },
        { label: 'Latency',  value: ping?.latency != null ? `${ping.latency}ms` : null },
        { label: 'Database', value: details.database },
        { label: 'Redis',    value: details.redis },
      ],
    },
    {
      icon: Brain,
      label: 'vit-ai',
      status: ai?.status ?? (aiLoading ? undefined : 'unknown'),
      isLoading: aiLoading,
      details: [
        { label: 'Models',   value: ai?.models_count ?? ai?.models },
        { label: 'Latency',  value: ai?.latency_ms != null ? `${ai.latency_ms}ms` : null },
        { label: 'Provider', value: ai?.provider },
      ],
    },
    {
      icon: HardDrive,
      label: 'vit-storage',
      status: details.storage ?? (pingLoading ? undefined : 'unknown'),
      isLoading: pingLoading,
      details: [
        { label: 'Providers', value: null },
        { label: 'Tachyon',   value: 'enabled' },
      ],
    },
    {
      icon: Database,
      label: 'PostgreSQL',
      status: details.database ?? (obsLoading ? undefined : 'unknown'),
      isLoading: obsLoading,
      details: [
        { label: 'Engine', value: 'PostgreSQL 16' },
      ],
    },
    {
      icon: Wifi,
      label: 'Redis / Valkey',
      status: details.redis ?? (obsLoading ? undefined : 'unknown'),
      isLoading: obsLoading,
      details: [
        { label: 'Cache', value: 'Valkey' },
      ],
    },
    {
      icon: Activity,
      label: 'AI / Tasks',
      status: details.ai ?? details.tasks ?? (obsLoading ? undefined : 'unknown'),
      isLoading: obsLoading,
      details: [
        { label: 'Agents',    value: details.tasks },
        { label: 'Inference', value: details.ai },
      ],
    },
  ]

  return (
    <div className="pt-16 min-h-screen">
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
                <Activity className="w-5 h-5 text-vit-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Platform Health</h1>
                <p className="text-white/50 text-sm">Live health data from all VIT production services</p>
              </div>
            </motion.div>
            <button onClick={() => refetch()} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-sm text-white/50 hover:text-white transition-colors">
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Overall status */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6 flex items-center justify-between">
          <div>
            <p className="text-sm text-white/50 mb-1">Overall Platform Status</p>
            <div className="flex items-center gap-3">
              <StatusBadge
                status={overallStatus === 'loading' ? undefined : overallStatus}
                size="sm"
                pulse={overallStatus === 'HEALTHY' || overallStatus === 'ok'}
              />
              <span className="text-lg font-semibold text-white capitalize">
                {overallStatus === 'loading' ? 'Checking…' : overallStatus}
              </span>
            </div>
          </div>
          {(obsLoading || summaryLoading) && <Spinner />}
        </motion.div>

        {/* Service cards */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {services.map((svc, i) => (
            <motion.div key={svc.label} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}>
              <ServiceCard {...svc} />
            </motion.div>
          ))}
        </div>

        {/* Subsystem detail from obs */}
        {obs?.subsystems && obs.subsystems.length > 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
            className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
            <h2 className="font-semibold text-white mb-4">Kernel Subsystems</h2>
            <div>
              {obs.subsystems.map((sub: any) => (
                <SubsystemRow key={sub.name} name={sub.name} status={sub.status} message={sub.message} />
              ))}
            </div>
          </motion.div>
        )}

        {/* Uptime note */}
        <div className="text-center text-xs text-white/20 py-4">
          Auto-refreshes every 30 seconds · Powered by <span className="text-vit-400/50">/api/obs/health</span> and <span className="text-vit-400/50">/api/system/health/summary</span>
        </div>
      </div>
    </div>
  )
}
