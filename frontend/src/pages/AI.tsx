import { motion } from 'framer-motion'
import { Brain, Zap, Activity, Cpu, RefreshCw, Server, Database, Layers } from 'lucide-react'
import { useAIHealth } from '@/hooks/useHealth'
import { useAIModels, useAIKernelStatus, useAIProviders, useAIVersion, useEnsembleStatus } from '@/hooks/useAI'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { StatCard } from '@/components/StatCard'
import { Spinner } from '@/components/ui/Spinner'
import { useQueryClient } from '@tanstack/react-query'
import type { Model } from '@/lib/api'
import { cn } from '@/lib/utils'

function EmptyNote({ message }: { message: string }) {
  return <p className="text-sm text-white/40 text-center py-6">{message}</p>
}

export default function AI() {
  const { data: health,  isLoading: healthLoading }    = useAIHealth()
  const { data: version }                               = useAIVersion()
  const { data: kernelStatus, isLoading: statusLoad }  = useAIKernelStatus()
  // providers is string[] e.g. ["internal", "ensemble"]
  const { data: providers,    isLoading: provLoad }    = useAIProviders()
  const { data: ensembleData, isLoading: ensLoad }     = useEnsembleStatus()
  const { data: models,       isLoading: modLoad }     = useAIModels()
  const qc = useQueryClient()

  const modelList: Model[]  = Array.isArray(models) ? models : []
  const providerList: string[] = Array.isArray(providers) ? providers : []

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
              Multi-provider AI inference engine with model registry, ensemble orchestration, and feature store.
              Data sourced live from <span className="font-mono text-white/70">vit-ai.onrender.com</span>.
            </p>
          </motion.div>
          <button
            onClick={refresh}
            disabled={healthLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/15 bg-white/5 hover:bg-white/10 text-white/70 hover:text-white text-sm transition-all"
          >
            <RefreshCw className={cn('w-4 h-4', healthLoading && 'animate-spin')} />
            Refresh
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Service Status',  value: health?.status ?? '—',                                         icon: Activity },
            { label: 'Version',         value: version?.version ?? '—',                                       icon: Cpu },
            { label: 'Response Time',   value: health?._latency != null ? `${health._latency}ms` : '—',      icon: Zap },
            { label: 'Models Loaded',   value: kernelStatus?.loaded_models_count != null ? kernelStatus.loaded_models_count : (modLoad ? '…' : modelList.length || '—'), icon: Brain },
          ].map((s, i) => <StatCard key={s.label} {...s} index={i} />)}
        </div>

        {/* Kernel status + Ensemble row */}
        <div className="grid sm:grid-cols-2 gap-4 mb-6">
          {/* Kernel */}
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="rounded-xl border border-white/10 bg-white/5 p-5"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Server className="w-4 h-4 text-vit-400" /> AI Kernel
              </h2>
              {statusLoad ? <Spinner className="w-4 h-4" /> : <StatusBadge status={kernelStatus?.status ?? health?.status} size="sm" pulse />}
            </div>
            {kernelStatus ? (
              <div className="space-y-2">
                {[
                  ['Status',        kernelStatus.status          ?? '—'],
                  ['Version',       kernelStatus.version         ?? '—'],
                  ['Models Loaded', kernelStatus.loaded_models_count != null ? String(kernelStatus.loaded_models_count) : '—'],
                  ['Mode',          kernelStatus.mode            ?? '—'],
                  ['Inferences',    kernelStatus.total_inferences != null ? String(kernelStatus.total_inferences) : '—'],
                  ['Avg Latency',   kernelStatus.avg_latency     != null ? String(kernelStatus.avg_latency) : '—'],
                ].map(([l, v]) => (
                  <div key={l} className="flex justify-between text-sm border-b border-white/5 pb-2 last:border-0 last:pb-0">
                    <span className="text-white/40">{l}</span>
                    <span className="text-white font-mono text-xs">{v as string}</span>
                  </div>
                ))}
              </div>
            ) : !statusLoad ? (
              <EmptyNote message="Kernel status unavailable" />
            ) : <div className="flex justify-center py-4"><Spinner /></div>}
          </motion.div>

          {/* Ensemble */}
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
            className="rounded-xl border border-white/10 bg-white/5 p-5"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-vit-400" /> Ensemble Engine
              </h2>
              {ensLoad ? <Spinner className="w-4 h-4" /> : <StatusBadge status={ensembleData?.status} size="sm" pulse />}
            </div>
            {ensembleData ? (
              <div className="space-y-2">
                {Object.entries(ensembleData)
                  .filter(([k]) => !k.startsWith('_'))
                  .map(([k, v]) => (
                    <div key={k} className="flex justify-between text-sm border-b border-white/5 pb-2 last:border-0 last:pb-0">
                      <span className="text-white/40 capitalize">{k.replace(/_/g, ' ')}</span>
                      <span className="text-white font-mono text-xs">{String(v ?? '—')}</span>
                    </div>
                  ))}
              </div>
            ) : !ensLoad ? (
              <EmptyNote message="Ensemble status unavailable" />
            ) : <div className="flex justify-center py-4"><Spinner /></div>}
          </motion.div>
        </div>

        {/* Providers */}
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6 mb-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-vit-400" /> Registered Providers
            </h2>
            {provLoad && <Spinner className="w-4 h-4" />}
          </div>
          {providerList.length > 0 ? (
            <div className="flex flex-wrap gap-3">
              {providerList.map(name => (
                <div key={name} className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/10 bg-white/5">
                  <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                  <span className="text-sm font-medium text-white capitalize">{name}</span>
                  <StatusBadge status="healthy" size="sm" />
                </div>
              ))}
            </div>
          ) : !provLoad ? (
            <EmptyNote message="No providers registered yet" />
          ) : <div className="flex justify-center py-4"><Spinner /></div>}
        </motion.div>

        {/* Model Registry */}
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-vit-400" /> Model Registry
              {modelList.length > 0 && (
                <span className="text-xs font-normal text-white/40 ml-1">({modelList.length} models)</span>
              )}
            </h2>
            {modLoad && <Spinner className="w-4 h-4" />}
          </div>
          {modelList.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10">
                    {['Model ID', 'Name', 'Provider', 'Task', 'Version', 'Status'].map(h => (
                      <th key={h} className="text-left text-white/40 font-medium pb-3 pr-5">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {modelList.map((m: any) => (
                    <tr key={m.id} className="border-b border-white/5 last:border-0">
                      <td className="py-3 pr-5 font-mono text-vit-300 text-xs">{m.id}</td>
                      <td className="py-3 pr-5 text-white/80">{m.name ?? '—'}</td>
                      <td className="py-3 pr-5 text-white/60">{m.provider ?? '—'}</td>
                      <td className="py-3 pr-5 text-white/40 text-xs">{m.task ?? '—'}</td>
                      <td className="py-3 pr-5 font-mono text-white/40 text-xs">{m.version ?? m.latest_version ?? '—'}</td>
                      <td className="py-3 pr-5"><StatusBadge status={m.status} size="sm" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : !modLoad ? (
            <div className="text-center py-10">
              <Brain className="w-8 h-8 text-white/20 mx-auto mb-3" />
              <p className="text-sm text-white/40 mb-1">No models registered yet</p>
              <p className="text-xs text-white/25 font-mono">POST /api/v1/models to register the first model</p>
            </div>
          ) : <div className="flex justify-center py-8"><Spinner /></div>}
        </motion.div>
      </div>
    </div>
  )
}
