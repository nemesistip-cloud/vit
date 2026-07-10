import { motion } from 'framer-motion'
import { RefreshCw, Activity, Server, Database, Brain, HardDrive, Wifi, Box } from 'lucide-react'
import { useAllHealth } from '@/hooks/useHealth'
import { useTachyonStatus } from '@/hooks/useStorage'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Spinner } from '@/components/ui/Spinner'
import { formatUptime } from '@/lib/utils'
import { useQueryClient } from '@tanstack/react-query'

function MetricRow({ label, value, mono = false }: { label: string; value?: string | number | boolean; mono?: boolean }) {
  if (value == null || value === '' || value === '—') return null
  const display = typeof value === 'boolean' ? (value ? 'true' : 'false') : String(value)
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-white/5 last:border-0">
      <span className="text-sm text-white/50">{label}</span>
      <span className={`text-sm text-white ${mono ? 'font-mono text-xs' : 'font-medium'}`}>{display}</span>
    </div>
  )
}

export default function Status() {
  const { gateway, ai, storage, isLoading, overallStatus } = useAllHealth()
  const { data: tachyon } = useTachyonStatus()
  const qc = useQueryClient()

  function refresh() {
    qc.invalidateQueries({ queryKey: ['health'] })
    qc.invalidateQueries({ queryKey: ['storage', 'tachyon-status'] })
  }

  // Real gateway health fields from production:
  // { status, version, models_loaded, db_connected, clv_tracking_enabled, uptime }
  const gw = gateway.data

  const services = [
    {
      label: 'VIT Gateway',
      icon: Server,
      status: gw?.status,
      isLoading: gateway.isLoading,
      details: [
        { label: 'Status',       value: gw?.status },
        { label: 'Version',      value: gw?.version },
        { label: 'Models Loaded',value: gw?.models_loaded },
        { label: 'DB Connected', value: gw?.db_connected != null ? (gw.db_connected ? 'yes' : 'no') : undefined },
        { label: 'CLV Tracking', value: gw?.clv_tracking_enabled != null ? (gw.clv_tracking_enabled ? 'enabled' : 'disabled') : undefined },
        { label: 'Uptime',       value: gw?.uptime ? formatUptime(gw.uptime) : undefined },
        { label: 'Latency',      value: gw?._latency != null ? `${gw._latency}ms` : undefined, mono: true },
      ],
    },
    {
      label: 'vit-ai',
      icon: Brain,
      status: ai.data?.status,
      isLoading: ai.isLoading,
      details: [
        { label: 'Status',  value: ai.data?.status },
        { label: 'Latency', value: ai.data?._latency != null ? `${ai.data._latency}ms` : undefined, mono: true },
      ],
    },
    {
      label: 'vit-storage',
      icon: HardDrive,
      status: storage.data?.status,
      isLoading: storage.isLoading,
      details: [
        { label: 'Status',   value: storage.data?.status },
        { label: 'Version',  value: storage.data?.version },
        { label: 'Plane',    value: storage.data?.plane },
        { label: 'Database', value: storage.data?.database },
        { label: 'Redis',    value: storage.data?.redis },
        { label: 'Latency',  value: storage.data?._latency != null ? `${storage.data._latency}ms` : undefined, mono: true },
      ],
    },
    {
      label: 'Tachyon Coordination',
      icon: Box,
      status: tachyon?.status,
      isLoading: false,
      details: [
        { label: 'Module',       value: tachyon?.module },
        { label: 'Version',      value: tachyon?.version },
        { label: 'Active Nodes', value: tachyon?.active_nodes != null ? String(tachyon.active_nodes) : undefined },
        { label: 'Manifests',    value: tachyon?.manifest_count != null ? String(tachyon.manifest_count) : undefined },
        { label: 'Total Bytes',  value: tachyon?.total_bytes != null ? String(tachyon.total_bytes) : undefined, mono: true },
      ],
    },
    {
      label: 'Storage Nodes',
      icon: Database,
      // Derive from tachyon providers or storage subsystems
      status: (() => {
        const nodes = tachyon?.providers ?? storage.data?.subsystems
        if (!nodes) return undefined
        const vals = Object.values(nodes) as any[]
        return vals.every(n => n.healthy) ? 'healthy' : 'degraded'
      })(),
      isLoading: false,
      details: Object.entries(tachyon?.providers ?? storage.data?.subsystems ?? {}).map(([name, info]: [string, any]) => ({
        label: name,
        value: info.healthy ? `healthy (${info.usage_pct != null ? (info.usage_pct * 100).toFixed(1) + '% used' : 'ok'})` : 'unhealthy',
      })),
    },
    {
      label: 'Redis / Valkey',
      icon: Wifi,
      status: storage.data?.redis?.includes('connected') && !storage.data.redis.includes('not_configured')
        ? 'connected'
        : 'not configured',
      isLoading: gateway.isLoading,
      details: [
        { label: 'Gateway',  value: (gw as any)?.redis?.status },
        { label: 'Storage',  value: storage.data?.redis },
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
            <p className="text-white/50">Live data from production — auto-refreshes every 30 seconds</p>
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

        {/* Overall banner */}
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6 flex items-center justify-between mb-8"
        >
          <div>
            <p className="text-sm text-white/50 mb-1">Overall Platform Status</p>
            <div className="flex items-center gap-3">
              <StatusBadge status={overallStatus === 'loading' ? undefined : overallStatus} pulse />
              <span className="text-lg font-semibold text-white capitalize">{overallStatus}</span>
            </div>
            {gw?.db_connected === false && (
              <p className="text-xs text-amber-400/70 mt-2">⚠ Gateway reports database disconnected — this degrades some features.</p>
            )}
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
              transition={{ delay: i * 0.06 }}
              className="rounded-xl border border-white/10 bg-white/5 p-5"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
                    <svc.icon className="w-4 h-4 text-vit-400" />
                  </div>
                  <span className="font-semibold text-white">{svc.label}</span>
                </div>
                {svc.isLoading ? <Spinner className="w-4 h-4" /> : <StatusBadge status={svc.status} size="sm" pulse />}
              </div>
              <div>
                {svc.details.map(d => (
                  <MetricRow key={d.label} label={d.label} value={d.value} mono={(d as any).mono} />
                ))}
                {svc.details.every(d => !d.value) && !svc.isLoading && (
                  <p className="text-sm text-white/30 text-center py-3">No metrics yet</p>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}
