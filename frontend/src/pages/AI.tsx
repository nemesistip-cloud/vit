import { motion } from 'framer-motion'
import { Brain, Zap, Activity, Cpu, RefreshCw } from 'lucide-react'
import { useAIHealth } from '@/hooks/useHealth'
import { useAIModels } from '@/hooks/useAI'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { StatCard } from '@/components/StatCard'
import { Spinner } from '@/components/ui/Spinner'
import { useQueryClient } from '@tanstack/react-query'

export default function AI() {
  const { data: health, isLoading: healthLoading } = useAIHealth()
  const { data: modelsData, isLoading: modelsLoading } = useAIModels()
  const qc = useQueryClient()

  const models    = health?.models ?? modelsData?.models ?? []
  const providers = health?.providers ?? []

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
              Multi-provider AI inference engine. Data sourced directly from the vit-ai service — never duplicated in the gateway.
            </p>
          </motion.div>
          <button onClick={refresh} disabled={healthLoading} className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/15 bg-white/5 hover:bg-white/10 text-white/70 hover:text-white text-sm transition-all">
            <RefreshCw className={`w-4 h-4 ${healthLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          {[
            { label: 'Service Status', value: health?.status ?? '—',           icon: Activity },
            { label: 'Version',        value: health?.version ?? '—',          icon: Cpu },
            { label: 'Latency',        value: health?._latency != null ? `${health._latency}ms` : '—', icon: Zap },
            { label: 'Models',         value: models.length > 0 ? models.length : '—', icon: Brain },
          ].map((s, i) => <StatCard key={s.label} {...s} index={i} />)}
        </div>

        {/* Inference Status */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6 mb-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Inference Engine</h2>
            {healthLoading ? <Spinner className="w-4 h-4" /> : (
              <StatusBadge status={(health as any)?.inference?.status ?? health?.status} pulse />
            )}
          </div>
          <div className="grid sm:grid-cols-3 gap-4">
            {[
              { label: 'Provider Count', value: providers.length > 0 ? providers.length : (health?.providers as any)?.length ?? '—' },
              { label: 'Inference Latency', value: (health as any)?.inference?.latency != null ? `${(health as any).inference.latency}ms` : (health?._latency != null ? `${health._latency}ms` : '—') },
              { label: 'Status', value: (health as any)?.inference?.status ?? health?.status ?? '—' },
            ].map(m => (
              <div key={m.label} className="bg-white/5 rounded-lg p-4">
                <p className="text-xs text-white/40 mb-1">{m.label}</p>
                <p className="text-lg font-semibold text-white font-mono">{m.value}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Providers */}
        {providers.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="rounded-xl border border-white/10 bg-white/5 p-6 mb-6"
          >
            <h2 className="text-lg font-semibold text-white mb-4">Provider Status</h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {providers.map((p: any) => (
                <div key={p.name} className="flex items-center justify-between p-4 rounded-lg bg-white/5 border border-white/10">
                  <div>
                    <p className="font-medium text-white text-sm">{p.name}</p>
                    {p.models != null && <p className="text-xs text-white/40">{p.models} models</p>}
                    {p.latency != null && <p className="text-xs font-mono text-vit-400">{p.latency}ms</p>}
                  </div>
                  <StatusBadge status={p.status} size="sm" pulse />
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Model Registry */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Model Registry</h2>
            {modelsLoading && <Spinner className="w-4 h-4" />}
          </div>
          {models.length === 0 && !modelsLoading ? (
            <div className="text-center py-10">
              <Brain className="w-8 h-8 text-white/20 mx-auto mb-3" />
              <p className="text-white/40 text-sm">No models returned by vit-ai — check the service logs.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left text-white/40 font-medium pb-3 pr-4">Model ID</th>
                    <th className="text-left text-white/40 font-medium pb-3 pr-4">Provider</th>
                    <th className="text-left text-white/40 font-medium pb-3 pr-4">Status</th>
                    <th className="text-right text-white/40 font-medium pb-3">Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((m: any) => (
                    <tr key={m.id} className="border-b border-white/5 last:border-0">
                      <td className="py-3 pr-4 font-mono text-white text-xs">{m.id}</td>
                      <td className="py-3 pr-4 text-white/60">{m.provider ?? '—'}</td>
                      <td className="py-3 pr-4"><StatusBadge status={m.status} size="sm" /></td>
                      <td className="py-3 text-right font-mono text-vit-400 text-xs">{m.latency != null ? `${m.latency}ms` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
