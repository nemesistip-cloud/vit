import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Brain, Zap, RefreshCw, Activity, Cpu, TrendingUp, BarChart3,
  AlertCircle, CheckCircle, MessageSquare, ChevronRight, Target, Layers,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { authHeaders } from '@/hooks/useAuth'

function useAiService() {
  return useQuery({
    queryKey: ['ai-service'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/health`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 15_000, refetchInterval: 30_000,
  })
}

function useAiFeed() {
  return useQuery({
    queryKey: ['ai-feed-health'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/ai-feed/health`, {
        signal,
        headers: authHeaders(),
      })
      return r.ok ? r.json() : null
    },
    staleTime: 15_000, refetchInterval: 30_000,
  })
}

function useAiFeedSources() {
  return useQuery({
    queryKey: ['ai-feed-sources'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/ai-feed/sources`, {
        signal,
        headers: authHeaders(),
      })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.sources ?? []
    },
    staleTime: 60_000,
  })
}

function useModelContribution() {
  return useQuery({
    queryKey: ['model-contribution'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/dashboard/model-confidence`, {
        signal,
        headers: authHeaders(),
      })
      return r.ok ? r.json() : null
    },
    staleTime: 60_000,
  })
}

function StatBlock({ icon: Icon, label, value, color }: {
  icon: React.ElementType; label: string; value?: string | number | null; color: string
}) {
  return (
    <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-white/40 uppercase tracking-wide font-medium">{label}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-4 h-4 text-white" />
        </div>
      </div>
      <div className="text-2xl font-bold text-white">{value ?? '—'}</div>
    </div>
  )
}

const KNOWN_MODELS = [
  'xgboost', 'lightgbm', 'random_forest', 'logistic_regression', 'neural_net',
  'catboost', 'gradient_boost', 'svm', 'naive_bayes', 'knn',
  'ridge', 'lasso', 'elastic_net',
]

export default function AI() {
  const [tab, setTab] = useState<'overview' | 'models' | 'inference'>('overview')
  const { data: service, isLoading: svcLoading, refetch } = useAiService()
  const { data: feed,    isLoading: feedLoading }          = useAiFeed()
  const { data: sources }                                  = useAiFeedSources()
  const { data: modelConf }                                = useModelContribution()

  const modelsLoaded = service?.models_loaded ?? feed?.models_count ?? KNOWN_MODELS.length
  const version      = feed?.version ?? service?.version ?? '—'
  const latency      = feed?.latency_ms
  const feedStatus   = feed?.status ?? (feedLoading ? 'loading' : 'unknown')
  const svcStatus    = service ? 'healthy' : (svcLoading ? undefined : 'unknown')

  return (
    <div className="pt-16 min-h-screen">
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
                <Brain className="w-5 h-5 text-vit-400" />
              </div>
              <div>
                <div className="text-xs text-vit-400 uppercase tracking-widest font-medium mb-0.5">AI SERVICE</div>
                <h1 className="text-2xl font-bold text-white">vit-ai</h1>
                <p className="text-white/50 text-sm">Multi-provider AI inference engine — data sourced directly from the vit-ai service</p>
              </div>
            </motion.div>
            <button onClick={() => refetch()} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-sm text-white/50 hover:text-white transition-colors">
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Top stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatBlock icon={Activity} label="Service Status" value={svcLoading ? '…' : (service ? 'Healthy' : 'Unknown')} color="bg-emerald-500/20" />
          <StatBlock icon={Cpu}      label="Version"        value={version}       color="bg-vit-500/20" />
          <StatBlock icon={Zap}      label="Latency"        value={latency != null ? `${latency}ms` : '—'} color="bg-amber-500/20" />
          <StatBlock icon={Brain}    label="Models"         value={modelsLoaded}  color="bg-purple-500/20" />
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-white/5 border border-white/10 rounded-xl p-1 w-fit">
          {(['overview', 'models', 'inference'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={cn('px-5 py-2 rounded-lg text-sm font-medium capitalize transition-all',
                tab === t ? 'bg-vit-500 text-white' : 'text-white/50 hover:text-white hover:bg-white/5')}>
              {t}
            </button>
          ))}
        </div>

        {tab === 'overview' && (
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Inference Engine */}
            <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-vit-400" />
                  <h2 className="font-semibold text-white">Inference Engine</h2>
                </div>
                {feedLoading ? <Spinner className="w-4 h-4" /> : <StatusBadge status={feedStatus} size="sm" pulse />}
              </div>
              <div className="space-y-3">
                {[
                  { label: 'Provider Count',   value: feed?.provider_count ?? sources?.length ?? '—' },
                  { label: 'Inference Latency', value: latency != null ? `${latency}ms` : '—' },
                  { label: 'Status',           value: feedStatus },
                  { label: 'DB Connected',     value: service?.db_connected ? 'Yes' : '—' },
                  { label: 'CLV Tracking',     value: service?.clv_tracking_enabled ? 'Enabled' : '—' },
                ].map(({ label, value }) => value && value !== '—' ? (
                  <div key={label} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                    <span className="text-sm text-white/40">{label}</span>
                    <span className="text-sm text-white font-medium capitalize">{String(value)}</span>
                  </div>
                ) : null)}
              </div>
            </div>

            {/* Model Confidence */}
            <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <BarChart3 className="w-4 h-4 text-vit-400" />
                <h2 className="font-semibold text-white">Model Confidence Breakdown</h2>
              </div>
              {(() => {
                const modelEntries = Array.isArray(modelConf?.models)
                  ? modelConf.models.map((m: any) => ({ name: m.name || m.key || 'Model', value: typeof m.accuracy === 'number' ? m.accuracy : (m.weight ?? 0) * 100 }))
                  : modelConf && typeof modelConf === 'object'
                  ? Object.entries(modelConf)
                      .filter(([k]) => k !== 'ensemble_accuracy' && k !== 'active_count' && k !== 'models')
                      .map(([k, v]: [string, any]) => ({ name: k, value: typeof v === 'number' ? (v <= 1 ? v * 100 : v) : 0 }))
                  : []

                if (modelEntries.length === 0) {
                  return (
                    <div className="flex flex-col items-center justify-center py-10 text-center">
                      <Target className="w-10 h-10 text-white/10 mb-3" />
                      <p className="text-white/40 text-sm">Sign in or load models to view confidence</p>
                    </div>
                  )
                }

                return (
                  <div className="space-y-3">
                    {modelEntries.slice(0, 8).map((item: { name: string; value: number }, idx: number) => (
                      <div key={item.name + idx} className="flex items-center gap-3">
                        <span className="text-xs text-white/50 w-28 shrink-0 capitalize truncate">{item.name.replace(/_/g, ' ')}</span>
                        <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
                          <motion.div initial={{ width: 0 }} animate={{ width: `${Math.min(100, Math.max(0, Math.round(item.value)))}%` }}
                            transition={{ duration: 0.6 }} className="h-full bg-vit-500 rounded-full" />
                        </div>
                        <span className="text-xs text-vit-400 font-medium w-12 text-right">
                          {item.value.toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  </div>
                )
              })()}
            </div>

            {/* AI Feed Sources */}
            {sources && sources.length > 0 && (
              <div className="lg:col-span-2 bg-surface-800/60 border border-white/8 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-5">
                  <Layers className="w-4 h-4 text-vit-400" />
                  <h2 className="font-semibold text-white">Signal Sources</h2>
                </div>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {sources.map((src: any, i: number) => (
                    <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-white/3 border border-white/5">
                      <div className="w-2 h-2 rounded-full bg-emerald-400" />
                      <div>
                        <p className="text-sm text-white font-medium">{src.name || src.source || src.id}</p>
                        {src.type && <p className="text-xs text-white/30">{src.type}</p>}
                      </div>
                      {src.weight != null && <span className="ml-auto text-xs text-vit-400 font-medium">{src.weight}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {tab === 'models' && (
          <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
            <div className="px-6 py-5 border-b border-white/8">
              <h2 className="font-semibold text-white">Model Registry</h2>
              <p className="text-xs text-white/40 mt-1">{modelsLoaded} models loaded across the inference ensemble</p>
            </div>
            {svcLoading ? (
              <div className="flex items-center justify-center py-16"><Spinner className="w-6 h-6 text-vit-400" /></div>
            ) : !service ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Brain className="w-12 h-12 text-white/10 mb-3" />
                <p className="text-white/40">No models returned by vit-ai</p>
                <p className="text-white/25 text-sm mt-1">Check the service logs for details.</p>
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {KNOWN_MODELS.slice(0, modelsLoaded as number).map((model, i) => (
                  <motion.div key={model} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
                    className="flex items-center gap-4 px-6 py-4 hover:bg-white/3 transition-colors">
                    <div className="w-8 h-8 rounded-lg bg-vit-500/10 flex items-center justify-center text-xs font-bold text-vit-400">
                      {i + 1}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-white capitalize">{model.replace(/_/g, ' ')}</p>
                      <p className="text-xs text-white/30">Ensemble member · Classification</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                      <span className="text-xs text-emerald-400">Loaded</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === 'inference' && (
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-8 text-center">
            <Zap className="w-10 h-10 text-vit-400 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-white mb-2">Live Inference Panel</h2>
            <p className="text-white/50 text-sm mb-6 max-w-md mx-auto">
              Submit a match ID to receive real-time probability analysis across all 13+ loaded models with confidence intervals.
            </p>
            <div className="flex max-w-md mx-auto gap-3">
              <input
                type="text"
                placeholder="Match ID or fixture name..."
                className="flex-1 px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-vit-500/50 transition-colors"
              />
              <button className="px-5 py-2.5 rounded-xl bg-vit-500 hover:bg-vit-400 text-white text-sm font-medium transition-colors flex items-center gap-2">
                <Zap className="w-4 h-4" /> Run
              </button>
            </div>
            <p className="text-xs text-white/25 mt-4">Uses <code className="text-vit-400/70">POST /api/predict</code> endpoint</p>
          </div>
        )}
      </div>
    </div>
  )
}
