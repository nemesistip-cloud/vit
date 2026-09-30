import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  CircleDashed,
  ShieldCheck,
  Sparkles,
  XCircle,
} from 'lucide-react'
import { authHeaders } from '@/hooks/useAuth'
import { ENDPOINTS } from '@/lib/api'

interface GenesisValidationResult {
  stage: number
  passed: boolean
  reason: string
}

interface GenesisState {
  current_stage: number
  completed_stages: number[]
  total_stages: number
  status: 'bootstrapping' | 'verified'
  verified: boolean
  updated_at?: string
  dependency_status?: {
    database: boolean
    redis: boolean
  }
  validation_results?: Record<string, GenesisValidationResult>
}

async function fetchGenesisStatus(): Promise<GenesisState> {
  const response = await fetch(`${ENDPOINTS.gateway}/api/genesis/status`, {
    headers: authHeaders(),
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || `Genesis status could not be loaded (${response.status})`)
  }

  return response.json()
}

const STAGES = [
  {
    id: 1,
    title: 'Platform Configuration',
    description: 'Confirm the local node configuration and operating currency baseline.',
    validation: 'The base currency must be configured and request margins must fall within 100–100,000 req/hr.',
  },
  {
    id: 2,
    title: 'Identity Configuration',
    description: 'Register the DID root of trust, resolver endpoint, and validator schema version.',
    validation: 'A DID resolver endpoint and validator schema must be configured.',
  },
  {
    id: 3,
    title: 'Governance Configuration',
    description: 'Set proposal cadence, voting quorum, and merit thresholds.',
    validation: 'Quorum must remain between 10% and 100%, and the voting window must be at least 24 hours.',
  },
  {
    id: 4,
    title: 'Blockchain Configuration',
    description: 'Establish VIT Chain boot parameters and block cadence targets.',
    validation: 'Chain ID must stay on 7764 and block time must fit between 5 and 60 seconds.',
  },
  {
    id: 5,
    title: 'Wallet Configuration',
    description: 'Route system fees and treasury allocations before funds begin moving.',
    validation: 'Burn and treasury shares must total exactly 100% across all fee flows.',
  },
  {
    id: 6,
    title: 'Genesis Treasury Creation',
    description: 'Confirm that at least one treasury pool is persisted.',
    validation: 'At least one treasury pool record must exist.',
  },
  {
    id: 7,
    title: 'Genesis VIT Coin Mint',
    description: 'Minting requires a reviewed supply plan, treasury destinations, and multi-party authorization.',
    validation: 'A validated supply allocation, treasury addresses, 2-of-3 signer approval, and chain height 0 are required.',
  },
  {
    id: 8,
    title: 'AI Service Initialization',
    description: 'Confirm active model metadata and an AI gateway URL are configured.',
    validation: 'At least three active models and an AI gateway URL must be configured.',
  },
  {
    id: 9,
    title: 'Storage Initialization',
    description: 'Confirm that the Tachyon provider pool is available.',
    validation: 'At least one storage provider must be available.',
  },
  {
    id: 10,
    title: 'Mainnet Readiness Verification',
    description: 'Run the final integration sweep across database, Redis, and genesis state.',
    validation: 'Database and Redis must be reachable, and all stage validations must pass.',
  },
] as const

export default function Genesis() {
  const queryClient = useQueryClient()
  const [activeStage, setActiveStage] = useState(1)

  const { data: genesisState, isLoading, error } = useQuery({
    queryKey: ['genesis-status'],
    queryFn: fetchGenesisStatus,
    staleTime: 30_000,
    refetchInterval: 30_000,
  })

  useEffect(() => {
    if (genesisState?.current_stage) {
      setActiveStage(genesisState.current_stage)
    }
  }, [genesisState?.current_stage])

  const completed = useMemo(() => new Set(genesisState?.completed_stages ?? []), [genesisState?.completed_stages])
  const progress = useMemo(() => {
    const total = genesisState?.total_stages ?? STAGES.length
    const count = Array.from(completed).filter(stage => genesisState?.validation_results?.[String(stage)]?.passed).length
    const percent = (count / total) * 100
    return Math.min(percent, 100)
  }, [completed, genesisState?.total_stages, genesisState?.validation_results])

  const currentStage = STAGES.find(stage => stage.id === activeStage) ?? STAGES[0]
  const activeValidation = genesisState?.validation_results?.[String(activeStage)] ?? {
    stage: activeStage,
    passed: false,
    reason: 'Live validation result is not available for this stage.',
  }
  const currentCompleted = genesisState?.verified === true || (completed.has(activeStage) && activeValidation.passed)
  const hasFailedValidations = Object.values(genesisState?.validation_results ?? {}).some(result => !result.passed)

  const advanceMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/genesis/advance`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage: activeStage + 1 }),
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        const detail = payload.detail
        const message = typeof detail === 'string' ? detail : detail?.validation?.reason ?? detail?.message
        throw new Error(message || `Stage advance failed (${response.status})`)
      }

      return response.json() as Promise<GenesisState>
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['genesis-status'], data)
      setActiveStage(data.current_stage)
    },
  })

  const advanceStage = () => {
    if (activeStage >= STAGES.length || activeStage !== genesisState?.current_stage) return
    advanceMutation.mutate()
  }

  const statusLabel = genesisState?.verified ? 'Verified' : activeValidation.passed ? 'Passed' : 'Blocked'
  const readinessChecks = [
    { label: 'Database connection', passed: genesisState?.dependency_status?.database },
    { label: 'Redis connection', passed: genesisState?.dependency_status?.redis },
    { label: 'Treasury pool exists', passed: genesisState?.validation_results?.['6']?.passed },
    { label: 'Model metadata is registered', passed: genesisState?.validation_results?.['7']?.passed },
    { label: 'AI service is configured', passed: genesisState?.validation_results?.['8']?.passed },
    { label: 'Storage provider is available', passed: genesisState?.validation_results?.['9']?.passed },
  ]

  return (
    <div className="space-y-6 pb-8">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl border border-vit-500/15 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.14),transparent_30%),linear-gradient(180deg,rgba(12,18,29,0.95),rgba(7,10,18,0.92))] p-6 shadow-[0_30px_80px_rgba(15,23,42,0.45)]"
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-emerald-300">
              <ShieldCheck className="h-3.5 w-3.5" />
              Bootstrap state
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-white/35">Network start-up</p>
              <h1 className="mt-2 text-3xl font-bold text-white">Genesis Initialization Wizard</h1>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white/70">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-vit-400" />
              {isLoading ? 'Loading bootstrap state...' : genesisState?.verified ? 'Production launch cleared' : hasFailedValidations ? 'Readiness checks need attention' : 'Readiness verification incomplete'}
            </div>
          </div>
        </div>

        {error ? (
          <div className="mt-4 rounded-2xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-200">
            {error.message}
          </div>
        ) : null}

        <div className="mt-6 space-y-3">
          <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-white/35">
            <span>Progress</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/5">
            <div
              className="h-full rounded-full bg-gradient-to-r from-vit-500 via-cyan-500 to-emerald-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </motion.div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-3xl border border-white/10 bg-surface-900/70 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Initialization stages</h2>
            <span className="text-xs uppercase tracking-[0.2em] text-white/35">10 steps</span>
          </div>

          <div className="space-y-3">
            {STAGES.map(stage => {
              const isActive = stage.id === activeStage
              const isDone = genesisState?.verified === true || (completed.has(stage.id) && genesisState?.validation_results?.[String(stage.id)]?.passed === true)

              return (
                <button
                  key={stage.id}
                  type="button"
                  onClick={() => setActiveStage(stage.id)}
                  className={`flex w-full items-center gap-3 rounded-2xl border p-3 text-left transition-all ${
                    isActive
                      ? 'border-vit-500/30 bg-vit-500/10'
                      : isDone
                        ? 'border-emerald-500/20 bg-emerald-500/5'
                        : 'border-white/8 bg-surface-800/50 hover:border-white/15 hover:bg-white/5'
                  }`}
                >
                  <div
                    className={`flex h-9 w-9 items-center justify-center rounded-xl border text-xs font-bold ${
                      isDone
                        ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-300'
                        : isActive
                          ? 'border-vit-500/25 bg-vit-500/10 text-vit-300'
                          : 'border-white/10 bg-white/5 text-white/40'
                    }`}
                  >
                    {isDone ? <CheckCircle2 className="h-4 w-4" /> : stage.id}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-sm font-medium text-white">Stage {stage.id}: {stage.title}</p>
                      <ChevronRight className="h-4 w-4 text-white/30" />
                    </div>
                    <p className="mt-1 text-xs text-white/45">{stage.description}</p>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-surface-900/70 p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-white/35">Current stage</p>
              <h2 className="mt-1 text-xl font-semibold text-white">{currentStage.title}</h2>
            </div>
            <div className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${
              currentCompleted
                ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                : 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
            }`}>
              {statusLabel}
            </div>
          </div>

          <p className="text-sm text-white/65">{currentStage.description}</p>

          <div className="mt-5 rounded-2xl border border-white/8 bg-black/20 p-4">
            <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-white/35">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-300" />
              Validation gate
            </div>
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="text-sm text-white/70">{currentStage.validation}</p>
              <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${
                activeValidation.passed
                  ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300'
                  : 'border-amber-500/20 bg-amber-500/10 text-amber-300'
              }`}>
                {activeValidation.passed ? 'Passed' : 'Failed'}
              </span>
            </div>
            <p className="text-sm leading-6 text-white/75">
              {activeValidation.reason}
            </p>
          </div>

          <div className="mt-5 space-y-3 rounded-2xl border border-white/8 bg-surface-800/60 p-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-white/55">Network lock</span>
              <span className={genesisState?.verified ? 'text-emerald-300' : 'text-amber-300'}>{genesisState?.verified ? 'Verified' : 'Locked'}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-white/55">Policy enforcement</span>
              <span className="text-white/75">Protected routes require verification</span>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={advanceStage}
              disabled={advanceMutation.isPending || activeStage >= STAGES.length || activeStage !== genesisState?.current_stage}
              className="inline-flex items-center gap-2 rounded-xl bg-vit-500/90 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-vit-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {advanceMutation.isPending ? 'Advancing...' : activeStage >= STAGES.length ? 'Genesis complete' : 'Advance to next stage'}
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
          {advanceMutation.error ? <p role="alert" className="mt-3 text-sm text-amber-200">{advanceMutation.error.message}</p> : null}
        </div>
      </div>

      <div className="rounded-3xl border border-white/10 bg-surface-900/70 p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-white/35">Readiness checklist</p>
            <h3 className="mt-1 text-lg font-semibold text-white">Production gates</h3>
          </div>
          <div className={`flex items-center gap-2 ${genesisState?.verified ? 'text-emerald-300' : 'text-amber-300'}`}>
            {genesisState?.verified ? <CheckCircle2 className="h-4 w-4" /> : <CircleDashed className="h-4 w-4" />}
            <span className="text-sm">{genesisState?.verified ? 'Verified' : 'System bootstrapping'}</span>
          </div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {readinessChecks.map((item) => (
            <div key={item.label} className="flex items-center gap-3 rounded-2xl border border-white/8 bg-white/3 p-3 text-sm text-white/70">
              {item.passed === true ? <CheckCircle2 className="h-4 w-4 text-emerald-300" /> : item.passed === false ? <XCircle className="h-4 w-4 text-amber-300" /> : <CircleDashed className="h-4 w-4 text-white/30" />}
              <span className="flex-1">{item.label}</span>
              <span className="text-xs text-white/45">{item.passed === true ? 'Passed' : item.passed === false ? 'Blocked' : 'Unavailable'}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
