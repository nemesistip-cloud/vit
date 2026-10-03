import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Brain, Zap, RefreshCw, Activity, Cpu, TrendingUp, BarChart3,
  AlertCircle, CheckCircle, MessageSquare, ChevronRight, Target, Layers,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS, type Model } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { authHeaders } from '@/hooks/useAuth'

function useAiService() {
  return useQuery({
    queryKey: ['ai-service'],
    queryFn: async ({ signal }) => {
      try {
        const r = await fetch(`${ENDPOINTS.gateway}/api/registry`, { signal })
        if (r.ok) {
          const reg = await r.json()
          if (reg?.services?.ai) return reg.services.ai
        }
      } catch {
        /* fallback to gateway health */
      }
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
      if (!r.ok) throw new Error(`AI feed health unavailable (${r.status})`)
      return r.json()
    },
    retry: false,
    staleTime: 15_000, refetchInterval: 30_000,
  })
}

function useAiModels() {
  return useQuery({
    queryKey: ['ai-model-registry'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/ai-feed/models`, {
        signal,
        headers: authHeaders(),
      })
      if (!r.ok) throw new Error(`AI model registry unavailable (${r.status})`)
      return r.json() as Promise<{ models?: Model[]; registered_count?: number }>
    },
    retry: false,
    staleTime: 60_000,
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

export default function AI() {
  const [tab, setTab] = useState<'overview' | 'models' | 'inference'>('overview')
  const [selectedModel, setSelectedModel] = useState('')
  const [promptInput, setPromptInput] = useState('')
  const [inferenceState, setInferenceState] = useState<{ loading: boolean; error: string | null; result: string | null }>({
    loading: false,
    error: null,
    result: null,
  })

  const { data: service, isLoading: svcLoading, refetch } = useAiService()
  const { data: feed, isLoading: feedLoading, error: feedError } = useAiFeed()
  const { data: modelRegistry, isLoading: modelsLoading, error: modelsError } = useAiModels()
  const { data: sources } = useAiFeedSources()
  const { data: modelConf } = useModelContribution()

  const modelsLoaded = service?.models_loaded ?? feed?.models_loaded ?? null
  const version = feed?.version ?? service?.version ?? null
  const latency = feed?.latency_ms ?? service?.latency_ms ?? null
  const rawModels = Array.isArray(modelRegistry?.models) ? modelRegistry.models : []
  const models = rawModels.filter((model: any) => model && (model.id || model.name || model.provider || model.status))
  const dbConnected = feed?.db_connected ?? service?.db_connected
  const clvEnabled = feed?.clv_tracking_enabled ?? service?.clv_tracking_enabled
  const feedStatus = feed?.status ?? (feedLoading ? 'loading' : feedError ? 'unavailable' : 'unknown')
  const serviceStatus = (feedError || modelsError || (modelsLoaded != null && modelsLoaded > 0 && models.length === 0))
    ? 'degraded'
    : (service?.status ?? feedStatus ?? 'unavailable')
  const hasServiceData = Boolean(service || feed || modelRegistry)
  const hasModels = models.length > 0

  useEffect(() => {
    if (!hasModels) {
      setSelectedModel('')
      return
    }
    setSelectedModel((current) => current || (models[0]?.id ?? models[0]?.name ?? ''))
  }, [hasModels, models])

  const handleInferenceRun = async () => {
    if (!selectedModel) {
      setInferenceState({ loading: false, error: 'Select a model from the registry before running inference.', result: null })
      return
    }
    if (!promptInput.trim()) {
      setInferenceState({ loading: false, error: 'Provide input before submitting a request.', result: null })
      return
    }

    setInferenceState({ loading: true, error: null, result: null })
    try {
      const response = await fetch(`${ENDPOINTS.gateway}/api/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(),
        },
        body: JSON.stringify({
          model: selectedModel,
          input: promptInput,
          parameters: {},
        }),
      })

      if (!response.ok) {
        throw new Error(`Inference request failed (${response.status})`)
      }

      const payload = await response.json()
      setInferenceState({ loading: false, error: null, result: JSON.stringify(payload, null, 2) })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Inference request failed. Confirm the VIT AI endpoint is reachable and credentials are valid.'
      setInferenceState({ loading: false, error: message, result: null })
    }
  }

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
          <StatBlock icon={Activity} label="Service Status" value={svcLoading ? 'Loading' : (serviceStatus || 'Unavailable')} color="bg-emerald-500/20" />
          <StatBlock icon={Cpu}      label="Version"        value={version ?? 'Unavailable'}       color="bg-vit-500/20" />
          <StatBlock icon={Zap}      label="Latency"        value={latency != null ? `${latency}ms` : '—'} color="bg-amber-500/20" />
          <StatBlock icon={Brain}    label="Loaded Models"  value={modelsLoaded}  color="bg-purple-500/20" />
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
                  { label: 'Provider Count',    value: feed?.provider_count ?? sources?.length ?? 1 },
                  { label: 'Inference Latency', value: latency != null ? `${latency}ms` : 'Unavailable' },
                  { label: 'Status',            value: feedStatus },
                  { label: 'DB Connected',      value: dbConnected == null ? 'Unavailable' : dbConnected ? 'Yes' : 'No' },
                  { label: 'CLV Tracking',      value: clvEnabled == null ? 'Unavailable' : clvEnabled ? 'Enabled' : 'Disabled' },
                ].map(({ label, value }) => value && value !== '—' ? (
                  <div key={label} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                    <span className="text-sm text-white/40">{label}</span>
                    <span className="text-sm text-white font-medium capitalize">{String(value)}</span>
                  </div>
                ) : null)}
                {feedError && <p className="pt-2 text-xs text-amber-300">AI feed health is unavailable; runtime details may be stale.</p>}
              </div>
            </div>

            {/* Model Confidence */}
            <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <BarChart3 className="w-4 h-4 text-vit-400" />
                <h2 className="font-semibold text-white">Historical Model Accuracy</h2>
              </div>
              {(() => {
                const modelEntries = Array.isArray(modelConf?.models)
                  ? modelConf.models.filter((m: any) => typeof m.accuracy === 'number' && Number.isFinite(m.accuracy)).map((m: any) => ({
                      name: m.name || m.key || 'Model',
                      value: m.accuracy,
                    }))
                  : []

                if (modelEntries.length === 0) {
                  return (
                    <div className="flex flex-col items-center justify-center py-10 text-center">
                      <Target className="w-10 h-10 text-white/10 mb-3" />
                      <p className="text-white/40 text-sm">No measured model accuracy is available yet</p>
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
              <p className="text-xs text-white/40 mt-1">{models.length} registered · {modelsLoaded ?? '—'} loaded in runtime</p>
            </div>
            {modelsLoading || svcLoading ? (
              <div className="flex items-center justify-center py-16"><Spinner className="w-6 h-6 text-vit-400" /></div>
            ) : modelsError ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Brain className="w-12 h-12 text-white/10 mb-3" />
                <p className="text-white/40">Model metadata is unavailable</p>
                <p className="text-white/25 text-sm mt-1">The AI service may be temporarily unreachable.</p>
              </div>
            ) : !hasServiceData && models.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Brain className="w-12 h-12 text-white/10 mb-3" />
                <p className="text-white/40">No model definitions are registered</p>
              </div>
            ) : models.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Brain className="w-12 h-12 text-white/10 mb-3" />
                <p className="text-white/40">No model definitions are registered</p>
                <p className="text-white/25 text-sm mt-1">The registry is empty even though the AI service reported {modelsLoaded ?? 0} loaded runtime model(s).</p>
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {models.map((model, i) => (
                  <motion.div key={model.id ?? model.name ?? i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
                    className="flex items-center gap-4 px-6 py-4 hover:bg-white/3 transition-colors">
                    <div className="w-8 h-8 rounded-lg bg-vit-500/10 flex items-center justify-center text-xs font-bold text-vit-400">
                      {i + 1}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-white capitalize">{model.name ?? model.id ?? 'Unnamed model'}</p>
                      <p className="text-xs text-white/30">{model.provider ?? 'Inference ensemble'}{model.status ? ` · ${model.status}` : ''}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                      <span className="text-xs text-emerald-400">Registered</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === 'inference' && (
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-8">
            <div className="max-w-3xl mx-auto">
              <div className="flex items-center justify-center mb-4">
                <Zap className="w-10 h-10 text-vit-400" />
              </div>
              <h2 className="text-lg font-semibold text-white text-center mb-2">Live Inference Panel</h2>
              <p className="text-white/50 text-sm mb-6 text-center max-w-lg mx-auto">
                Select a deployed model, submit a prompt or payload, and inspect the actual response returned by the service.
              </p>

              {hasModels ? (
                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-[220px,1fr]">
                    <label className="space-y-2">
                      <span className="text-xs uppercase tracking-wide text-white/40">Model</span>
                      <select
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-vit-500/50"
                      >
                        {models.map((model: any) => (
                          <option key={model.id ?? model.name} value={model.id ?? model.name} className="bg-surface-900 text-white">
                            {model.name ?? model.id ?? 'Unnamed model'}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="space-y-2">
                      <span className="text-xs uppercase tracking-wide text-white/40">Input</span>
                      <input
                        value={promptInput}
                        onChange={(e) => setPromptInput(e.target.value)}
                        type="text"
                        placeholder="Enter a prompt or fixture context..."
                        className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-vit-500/50 transition-colors"
                      />
                    </label>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <button
                      onClick={handleInferenceRun}
                      disabled={inferenceState.loading}
                      className="px-5 py-2.5 rounded-xl bg-vit-500 hover:bg-vit-400 disabled:opacity-60 text-white text-sm font-medium transition-colors flex items-center gap-2"
                    >
                      <Zap className="w-4 h-4" /> {inferenceState.loading ? 'Running...' : 'Run'}
                    </button>
                    <span className="text-xs text-white/25">Uses <code className="text-vit-400/70">POST /api/predict</code> endpoint</span>
                  </div>

                  {inferenceState.error && (
                    <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
                      {inferenceState.error}
                    </div>
                  )}

                  {inferenceState.result && (
                    <div className="rounded-xl border border-white/10 bg-black/20 p-4 text-left">
                      <p className="text-xs uppercase tracking-wide text-white/40 mb-2">Response</p>
                      <pre className="text-xs whitespace-pre-wrap text-white/80 overflow-x-auto">{JSON.stringify(inferenceState.result, null, 2)}</pre>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <Brain className="w-12 h-12 text-white/10 mb-3" />
                  <p className="text-white/40">No registered models are available for live inference</p>
                  <p className="text-white/25 text-sm mt-1">The AI service registry is currently empty or unavailable.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
