import { motion } from 'framer-motion'
import { RefreshCw, Activity, Server, Database, Brain, HardDrive, Wifi } from 'lucide-react'
import { useAllHealth } from '@/hooks/useHealth'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Spinner } from '@/components/ui/Spinner'
import { formatUptime } from '@/lib/utils'
import { useQueryClient } from '@tanstack/react-query'

function MetricRow({ label, value, mono = false }: { label: string; value?: string | number; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-white/5 last:border-0">
      <span className="text-sm text-white/50">{label}</span>
      <span className={`text-sm text-white ${mono ? 'font-mono' : 'font-medium'}`}>{value ?? '—'}</span>
    </div>
  )
}

export default function Status() {
  const { gateway, ai, storage, isLoading, overallStatus } = useAllHealth()
  const qc = useQueryClient()

  function refresh() {
    qc.invalidateQueries({ queryKey: ['health'] })
  }

  const services = [
    {
      label: 'VIT Gateway',
      icon: Server,
      status: gateway.data?.status,
      latency: gateway.data?._latency,
      isLoading: gateway.isLoading,
      details: [
        { label: 'Version',     value: gateway.data?.version },
        { label: 'Environment', value: gateway.data?.environment },
        { label: 'Uptime',      value: gateway.data?.uptime ? formatUptime(gateway.data.uptime) : undefined },
        { label: 'Latency',     value: gateway.data?._latency != null ? `${gateway.data._latency}ms` : undefined, mono: true },
      ],
    },
    {
      label: 'vit-ai',
      icon: Brain,
      status: ai.data?.status,
      latency: ai.data?._latency,
      isLoading: ai.isLoading,
      details: [
        { label: 'Version', value: ai.data?.version },
        { label: 'Latency', value: ai.data?._latency != null ? `${ai.data._latency}ms` : undefined, mono: true },
        { label: 'Inference', value: (ai.data as any)?.inference?.status },
      ],
    },
    {
      label: 'vit-storage',
      icon: HardDrive,
      status: storage.data?.status,
      latency: storage.data?._latency,
      isLoading: storage.isLoading,
      details: [
        { label: 'Version', value: storage.data?.version },
        { label: 'Latency', value: storage.data?._latency != null ? `${storage.data._latency}ms` : undefined, mono: true },
      ],
    },
    {
      label: 'PostgreSQL',
      icon: Database,
      status: (gateway.data as any)?.postgres?.status ?? gateway.data?.status,
      latency: (gateway.data as any)?.postgres?.latency,
      isLoading: gateway.isLoading,
      details: [
        { label: 'Status',  value: (gateway.data as any)?.postgres?.status },
        { label: 'Latency', value: (gateway.data as any)?.postgres?.latency != null ? `${(gateway.data as any).postgres.latency}ms` : undefined, mono: true },
      ],
    },
    {
      label: 'Redis / Valkey',
      icon: Wifi,
      status: (gateway.data as any)?.redis?.status ?? gateway.data?.status,
      latency: (gateway.data as any)?.redis?.latency,
      isLoading: gateway.isLoading,
      details: [
        { label: 'Status',  value: (gateway.data as any)?.redis?.status },
        { label: 'Latency', value: (gateway.data as any)?.redis?.latency != null ? `${(gateway.data as any).redis.latency}ms` : undefined, mono: true },
      ],
    },
  ]

  return (
    <div className="pt-24 pb-16">
      <div className="max-w-5xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-5 h-5 text-vit-400" />
              <span className="text-sm text-vit-400 font-medium uppercase tracking-wider">System Status</span>
            </div>
            <h1 className="text-4xl font-bold text-white mb-2">Platform Health</h1>
            <p className="text-white/50">Live health data from all VIT production services</p>
          </motion.div>
          <button
            onClick={refresh}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/15 bg-white/5 hover:bg-white/10 text-white/70 hover:text-white text-sm transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Overall status banner */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6 flex items-center justify-between mb-8"
        >
          <div>
            <p className="text-sm text-white/50 mb-1">Overall Platform Status</p>
            <div className="flex items-center gap-3">
              <StatusBadge status={overallStatus === 'loading' ? undefined : overallStatus} pulse />
              <span className="text-lg font-semibold text-white capitalize">{overallStatus}</span>
            </div>
          </div>
          {isLoading && <Spinner />}
        </motion.div>

        {/* Service cards */}
        <div className="grid sm:grid-cols-2 gap-4">
          {services.map((svc, i) => (
            <motion.div
              key={svc.label}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07 }}
              className="rounded-xl border border-white/10 bg-white/5 p-5"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
                    <svc.icon className="w-4.5 h-4.5 text-vit-400" />
                  </div>
                  <span className="font-semibold text-white">{svc.label}</span>
                </div>
                {svc.isLoading ? <Spinner className="w-4 h-4" /> : <StatusBadge status={svc.status} size="sm" pulse />}
              </div>
              <div>
                {svc.details.map(d => (
                  d.value ? <MetricRow key={d.label} label={d.label} value={d.value} mono={d.mono} /> : null
                ))}
                {svc.details.every(d => !d.value) && !svc.isLoading && (
                  <p className="text-sm text-white/30 text-center py-2">No additional metrics</p>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}
