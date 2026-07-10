import { motion } from 'framer-motion'
import { Brain, Zap, Activity, Cpu, RefreshCw, Server, Database } from 'lucide-react'
import { useAIHealth } from '@/hooks/useHealth'
import { useAIModels, useAIKernelStatus, useAIProviders, useAIVersion } from '@/hooks/useAI'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { StatCard } from '@/components/StatCard'
import { Spinner } from '@/components/ui/Spinner'
import { useQueryClient } from '@tanstack/react-query'
import type { Provider, Model } from '@/lib/api'
import { cn } from '@/lib/utils'

function EmptyState({ icon: Icon, message }: { icon: React.ElementType; message: string }) {
  return (
    <div className="text-center py-12 flex flex-col items-center gap-3">
      <Icon className="w-8 h-8 text-white/20" />
      <p className="text-sm text-white/40">{message}</p>
    </div>
  )
}

export default function AI() {
  const { data: health, isLoading: healthLoading }     = useAIHealth()
  const { data: version }                               = useAIVersion()
  const { data: kernelStatus, isLoading: statusLoading } = useAIKernelStatus()
  const { data: providers,    isLoading: provLoading }  = useAIProviders()
  const { data: models,       isLoading: modelsLoading } = useAIModels()
  const qc = useQueryClient()

  const modelList:    Model[]    = Array.isArray(models)    ? models    : (models as any)?.models    ?? []
  const providerList: Provider[] = Array.isArray(providers) ? providers : (providers as any)?.providers ?? []

  const isLoading = healthLoading || statusLoading

  function refresh() {
    qc.invalidateQueries({ queryKey: ['health', 'ai'] })
    qc.invalidateQueries({ queryKey: ['ai'] })
  }

  return (
    <div className="pt-24 pb-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">

        {/* Header */}
        <div className="flex items-start justify-between mb-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-5 h-5 text-vit-400" />
              <span className="text-sm text-vit-400 font-medium uppercase tracking-wider">AI Service</span>
            </div>
            <h1 className="text-4xl font-bold text-white mb-2">vit-ai</h1>
            <p className="text-white/50 max-w-lg">
              Multi-provider AI inference engine. Data sourced directly from vit-ai — never duplicated in the gateway.
            </p>
          </motion.div>
          <button
            onClick={refresh}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/15 bg-white/5 hover:bg-white/10 text-white/70 hover:text-white text-sm transition-all"
          >
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
            Refresh
          </button>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Service Status', value: health?.status         ?? '—', icon: Activity },
            { label: 'Version',        value: version?.version       ?? health?._latency != null ? (version?.version ?? '—') : '—', icon: Cpu },
            { label: 'Response Time',  value: health?._latency != null ? `${health._latency}ms` : '—', icon: Zap },
            { label: 'Models',         value: modelList.length > 0 ? modelList.length : (modelsLoading ? '…' : '—'), icon: Brain },
          ].map((s, i) => <StatCard key={s.label} {...s} index={i} />)}
        </div>

        {/* Kernel / Inference status */}
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6 mb-6"
        >
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Server className="w-4 h-4 text-vit-400" /> AI Kernel Status
            </h2>
            {statusLoading
              ? <Spinner className="w-4 h-4" />
              : <StatusBadge status={(kernelStatus as any)?.status ?? health?.status} pulse />}
          </div>

          {kernelStatus ? (
            <div className="grid sm:grid-cols-3 gap-4">
              {[
                { label: 'Kernel State',  value: (kernelStatus as any)?.status          ?? '—' },
                { label: 'Mode',          value: (kernelStatus as any)?.mode            ?? '—' },
                { label: 'Uptime',        value: (kernelStatus as any)?.uptime          ?? '—' },
                { label: 'Total Infer.',  value: (kernelStatus as any)?.total_inferences ?? '—' },
                { label: 'Error Rate',    value: (kernelStatus as any)?.error_rate       ?? '—' },
                { label: 'Avg Latency',   value: (kernelStatus as any)?.avg_latency      ?? (kernelStatus as any)?.latency ?? '—' },
              ].map(m => (
                <div key={m.label} className="bg-white/5 rounded-lg p-4">
                  <p className="text-xs text-white/40 mb-1">{m.label}</p>
                  <p className="text-base font-semibold text-white font-mono">{String(m.value)}</p>
                </div>
              ))}
            </div>
          ) : !statusLoading ? (
            <EmptyState icon={Server} message="Kernel status unavailable — endpoint may require authentication." />
          ) : (
            <div className="flex justify-center py-8"><Spinner /></div>
          )}
        </motion.div>

        {/* Providers */}
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6 mb-6"
        >
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-vit-400" /> Provider Status
            </h2>
            {provLoading && <Spinner className="w-4 h-4" />}
          </div>

          {providerList.length > 0 ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {providerList.map((p: any) => (
                <div key={p.name ?? p.id} className="flex items-start justify-between p-4 rounded-lg bg-white/5 border border-white/10">
                  <div>
                    <p className="font-medium text-white text-sm">{p.name ?? p.id}</p>
                    {p.models != null  && <p className="text-xs text-white/40 mt-0.5">{p.models} models</p>}
                    {p.latency != null && <p className="text-xs font-mono text-vit-400 mt-0.5">{p.latency}ms</p>}
                    {p.type    != null && <p className="text-xs text-white/30 mt-0.5">{p.type}</p>}
                  </div>
                  <StatusBadge status={p.status ?? p.health} size="sm" pulse />
                </div>
              ))}
            </div>
          ) : !provLoading ? (
            <EmptyState icon={Zap} message="No providers returned — endpoint may require authentication or providers are not yet registered." />
          ) : (
            <div className="flex justify-center py-8"><Spinner /></div>
          )}
        </motion.div>

        {/* Model Registry */}
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6"
        >
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-vit-400" /> Model Registry
            </h2>
            {modelsLoading && <Spinner className="w-4 h-4" />}
          </div>

          {modelList.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10">
                    {['Model ID', 'Name', 'Provider', 'Version', 'Status'].map(h => (
                      <th key={h} className="text-left text-white/40 font-medium pb-3 pr-6">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {modelList.map((m: any) => (
                    <tr key={m.id} className="border-b border-white/5 last:border-0">
                      <td className="py-3 pr-6 font-mono text-vit-300 text-xs">{m.id}</td>
                      <td className="py-3 pr-6 text-white/80 text-sm">{m.name ?? '—'}</td>
                      <td className="py-3 pr-6 text-white/60 text-sm">{m.provider ?? '—'}</td>
                      <td className="py-3 pr-6 font-mono text-white/40 text-xs">{m.version ?? (m.latest_version ?? '—')}</td>
                      <td className="py-3 pr-6"><StatusBadge status={m.status} size="sm" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : !modelsLoading ? (
            <EmptyState icon={Brain} message="No models in registry yet — use POST /api/v1/models to register the first model." />
          ) : (
            <div className="flex justify-center py-8"><Spinner /></div>
          )}
        </motion.div>

      </div>
    </div>
  )
}
