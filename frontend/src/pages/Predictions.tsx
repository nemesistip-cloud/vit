import { useState } from 'react'
import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Brain, Target, CheckCircle, XCircle, Clock, Filter,
  TrendingUp, BarChart3, ChevronRight, Link2, CheckCircle2,
  AlertCircle, Loader2,
} from 'lucide-react'
import { cn, timeAgo } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { getAuthToken, authHeaders } from '@/hooks/useAuth'

type OutcomeFilter = 'all' | 'won' | 'lost' | 'pending'

function ProvenanceBadge({ source }: { source?: string }) {
  if (!source) return null
  const s = source.toLowerCase()
  const isLive = s.includes('live') || s.includes('provider') || s.includes('isports')
  const isFallback = s.includes('fallback') || s.includes('scie')
  const isSeed = s.includes('seed') || s.includes('demo')

  return (
    <span className={cn(
      'px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border',
      isLive ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' :
      isFallback ? 'bg-amber-500/15 text-amber-300 border-amber-500/30' :
      isSeed ? 'bg-purple-500/15 text-purple-300 border-purple-500/30' :
      'bg-vit-500/15 text-vit-300 border-vit-500/30'
    )}>
      {isLive ? 'LIVE' : isFallback ? 'SCIE FALLBACK' : isSeed ? 'DEMO SEED' : 'ENSEMBLE'}
    </span>
  )
}


function usePredictions(outcome: OutcomeFilter) {
  return useQuery({
    queryKey: ['predictions', outcome],
    queryFn: async ({ signal }) => {
      const params = outcome !== 'all' ? `?outcome=${outcome}` : ''
      const r = await fetch(`${ENDPOINTS.gateway}/api/predict/history${params}`, { signal, headers: authHeaders() })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.predictions ?? d.items ?? []
    },
    retry: false, staleTime: 60_000,
  })
}

function useAccuracy() {
  return useQuery({
    queryKey: ['prediction-accuracy'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/predict/accuracy`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : null
    },
    retry: false, staleTime: 300_000,
  })
}

function OutcomeChip({ outcome }: { outcome?: string }) {
  if (!outcome) return <span className="px-2 py-0.5 rounded-full bg-white/10 text-white/40 text-xs">Pending</span>
  const o = outcome.toLowerCase()
  if (o === 'won' || o === 'win' || o === 'correct')
    return <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-medium"><CheckCircle className="w-3 h-3" />Won</span>
  if (o === 'lost' || o === 'loss' || o === 'incorrect')
    return <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 text-xs font-medium"><XCircle className="w-3 h-3" />Lost</span>
  return <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 text-xs font-medium"><Clock className="w-3 h-3" />Pending</span>
}

// ── On-chain attestation button ───────────────────────────────────────────────

type AttestState = 'idle' | 'loading' | 'done' | 'error'

function AttestButton({ predictionId }: { predictionId: number }) {
  const [state, setState] = useState<AttestState>('idle')
  const [result, setResult] = useState<{ hash: string; method: string } | null>(null)
  const [errMsg, setErrMsg] = useState('')

  const mutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/predictions/${predictionId}/attest`, {
        method: 'POST',
        headers: authHeaders(),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? d.message ?? 'Attestation failed')
      return d
    },
    onMutate: () => setState('loading'),
    onSuccess: (d: any) => {
      setState('done')
      setResult({ hash: d.attestation_hash, method: d.method })
    },
    onError: (e: Error) => { setState('error'); setErrMsg(e.message) },
  })

  if (state === 'done' && result) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-emerald-400">
        <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
        <span className="font-mono truncate max-w-[140px]" title={result.hash}>{result.hash.slice(0, 18)}…</span>
        <span className="text-white/20">·</span>
        <span className="text-white/30">{result.method === 'chain' ? 'on-chain' : 'hash proof'}</span>
      </div>
    )
  }

  if (state === 'error') {
    return (
      <div className="flex items-center gap-1.5 text-xs text-red-400">
        <AlertCircle className="w-3.5 h-3.5" />
        <span className="truncate max-w-[160px]">{errMsg}</span>
      </div>
    )
  }

  return (
    <button
      onClick={() => mutation.mutate()}
      disabled={state === 'loading'}
      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-white/40 hover:text-white/70 text-xs font-medium transition-all disabled:opacity-50"
    >
      {state === 'loading'
        ? <Loader2 className="w-3 h-3 animate-spin" />
        : <Link2 className="w-3 h-3" />}
      {state === 'loading' ? 'Attesting…' : 'Attest on-chain'}
    </button>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Predictions() {
  const navigate = useNavigate()
  const token    = getAuthToken()
  useEffect(() => { if (!token) navigate('/login', { replace: true }) }, [token, navigate])

  const [filter, setFilter] = useState<OutcomeFilter>('all')
  const { data, isLoading }  = usePredictions(filter)
  const { data: accuracy }   = useAccuracy()

  if (!token) return <div className="pt-16 min-h-screen flex items-center justify-center"><Spinner className="w-8 h-8 text-vit-400" /></div>

  return (
    <div className="pt-16 min-h-screen">
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
              <Brain className="w-5 h-5 text-vit-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">My Predictions</h1>
              <p className="text-white/50 text-sm">Your AI-assisted prediction history, accuracy stats, and on-chain attestations</p>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Accuracy stats */}
        {accuracy && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Total Predictions', value: accuracy.total ?? '—',                                               icon: Brain,     color: 'bg-vit-500/20'     },
              { label: 'Win Rate',          value: accuracy.win_rate != null ? `${(accuracy.win_rate * 100).toFixed(1)}%` : '—', icon: Target,    color: 'bg-emerald-500/20' },
              { label: 'Current Streak',    value: accuracy.current_streak ?? '—',                                      icon: TrendingUp, color: 'bg-amber-500/20'   },
              { label: 'Best League',       value: accuracy.best_league ?? '—',                                         icon: BarChart3,  color: 'bg-purple-500/20'  },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-white/40 uppercase tracking-wide">{label}</span>
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${color}`}>
                    <Icon className="w-3.5 h-3.5 text-white" />
                  </div>
                </div>
                <div className="text-xl font-bold text-white">{value}</div>
              </div>
            ))}
          </div>
        )}

        {/* On-chain attestation explainer */}
        <div className="flex items-start gap-3 p-4 rounded-xl border border-vit-500/20 bg-vit-500/5">
          <Link2 className="w-4 h-4 text-vit-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-vit-300">On-chain attestation</p>
            <p className="text-xs text-white/40 mt-0.5">
              Each prediction can be anchored to the VIT chain as an immutable proof. Click <strong className="text-white/60">Attest on-chain</strong> on any prediction to generate a cryptographic hash recorded on-chain — trustless verification of your prediction history.
            </p>
          </div>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex gap-1 bg-white/5 border border-white/10 rounded-xl p-1">
            {(['all', 'won', 'lost', 'pending'] as OutcomeFilter[]).map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={cn('px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all',
                  filter === f ? 'bg-vit-500 text-white' : 'text-white/50 hover:text-white hover:bg-white/5')}>
                {f}
              </button>
            ))}
          </div>
          <span className="text-xs text-white/30 ml-auto">{data?.length ?? 0} predictions</span>
        </div>

        {/* Prediction list */}
        {isLoading ? (
          <div className="flex items-center justify-center py-24"><Spinner className="w-8 h-8 text-vit-400" /></div>
        ) : !data || data.length === 0 ? (
          <div className="text-center py-24">
            <Brain className="w-14 h-14 text-white/10 mx-auto mb-4" />
            <p className="text-white/50 font-medium">No predictions yet</p>
            <p className="text-white/30 text-sm mt-1">Browse matches and make your first AI-powered prediction.</p>
            <a href="/matches" className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-xl bg-vit-500/20 text-vit-400 text-sm hover:bg-vit-500/30 transition-colors">
              Browse Matches <ChevronRight className="w-4 h-4" />
            </a>
          </div>
        ) : (
          <div className="space-y-3">
            {data.map((pred: any, i: number) => {
              const predictionId = pred.id ?? pred.prediction_id ?? null
              const outcome = pred.outcome ?? (pred.was_correct === true ? 'won' : pred.was_correct === false ? 'lost' : 'pending')
              return (
                <motion.div key={predictionId ?? i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
                  className="bg-surface-800/60 border border-white/8 rounded-xl p-5 hover:border-white/15 transition-colors">
                  <div className="flex items-start justify-between gap-4 flex-wrap">
                    <div>
                      <p className="font-medium text-white">{pred.home_team} vs {pred.away_team}</p>
                      <p className="text-sm text-white/40 mt-0.5">{pred.league}</p>
                      {pred.created_at && <p className="text-xs text-white/25 mt-1">{timeAgo(pred.created_at)}</p>}
                    </div>
                    <div className="flex items-center gap-3 flex-wrap">
                      {pred.bet_side && (
                        <span className="px-2.5 py-1 rounded-lg bg-vit-500/15 text-vit-300 text-xs font-medium uppercase">{pred.bet_side}</span>
                      )}
                      {pred.confidence != null && (
                        <span className="flex items-center gap-1 text-sm text-vit-400 font-medium">
                          <Target className="w-3.5 h-3.5" />{Math.round(pred.confidence * 100)}%
                        </span>
                      )}
                      <ProvenanceBadge source={pred.provenance ?? pred.data_provenance?.data_source} />
                      <OutcomeChip outcome={outcome} />
                    </div>
                  </div>

                  {pred.entry_odds != null && (
                    <div className="mt-3 pt-3 border-t border-white/6 flex gap-6 text-xs text-white/40">
                      <span>Odds: <span className="text-white/70">{pred.entry_odds}</span></span>
                      {pred.final_ev != null && <span>EV: <span className={pred.final_ev > 0 ? 'text-emerald-400' : 'text-red-400'}>{pred.final_ev > 0 ? '+' : ''}{pred.final_ev.toFixed(3)}</span></span>}
                      {pred.clv_earned != null && <span>CLV: <span className="text-vit-400">+{pred.clv_earned}</span></span>}
                    </div>
                  )}

                  {/* On-chain attestation */}
                  {predictionId && (
                    <div className="mt-3 pt-3 border-t border-white/6 flex items-center justify-between">
                      <span className="text-xs text-white/20">Chain proof</span>
                      <AttestButton predictionId={predictionId} />
                    </div>
                  )}
                </motion.div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
