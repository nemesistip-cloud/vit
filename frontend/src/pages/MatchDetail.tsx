import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  Calendar,
  AlertCircle,
  Brain,
  Target,
  TrendingUp,
  Activity,
  Users,
  BarChart3,
  Zap,
  CheckCircle2,
  Flame,
  Clock,
  RefreshCw,
  Play,
  ShieldCheck,
  Database,
} from 'lucide-react'
import { ENDPOINTS } from '@/lib/api'
import { cn } from '@/lib/utils'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Spinner } from '@/components/ui/Spinner'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Prediction {
  model_name: string
  model_type?: string
  bet_side?: string
  confidence: number
  final_ev?: number
  entry_odds?: number
  reasoning?: string
  accuracy_overall?: number
}

interface Match {
  id: number
  match_id?: number
  home_team: string
  away_team: string
  league: string
  sport?: string
  kickoff_time: string
  status: string
  prediction_status?: 'not_initialized' | 'initializing' | 'ready' | 'failed' | 'stale'
  prediction_source?: 'live_generated' | 'seed_demo'
  is_seed?: boolean
  job_id?: string
  error_message?: string
  provenance?: {
    job_id?: string
    source?: string
    external_id?: string
    model_version?: string
    generated_at?: string
    feature_completeness?: number
    odds_snapshot?: { home?: number; draw?: number; away?: number }
    data_snapshot?: Record<string, unknown>
  }
  source?: string
  data_status?: 'LIVE' | 'CACHED' | 'DEGRADED' | 'UNAVAILABLE'
  data_provenance?: {
    data_source?: string
    source_type?: string
    retrieved_at?: string
    fallback_used?: boolean
  }
  home_score?: number
  away_score?: number
  home_prob?: number
  draw_prob?: number
  away_prob?: number
  over_25_prob?: number
  under_25_prob?: number
  btts_prob?: number
  no_btts_prob?: number
  dnb_home_prob?: number
  dnb_away_prob?: number
  confidence?: number
  edge?: number
  venue?: string
  referee?: string
  attendance?: number
  odds?: { home?: number; draw?: number; away?: number }
  intelligence?: {
    consensus?: {
      home_prob?: number
      draw_prob?: number
      away_prob?: number
      confidence?: number
      risk_score?: number
      model_agreement?: number
      models_active?: number
      elo_diff?: number
      squad_value_diff?: number
      timestamp?: string
    }
    attribution?: Prediction[]
    tactical?: {
      summary?: string
      key_factors?: string[]
      recommendation?: string
    }
    market_edge?: {
      ai_prob?: number
      bookmaker_prob?: number
      edge?: number
      expected_roi?: number
      kelly_stake?: number
    }
  }
}

function normalizeMatch(payload: unknown): Match | null {
  if (!payload || typeof payload !== 'object') return null

  const row = payload as Record<string, unknown>
  const matchId = Number(row.id ?? row.match_id)
  if (!Number.isFinite(matchId) || matchId <= 0) return null

  return {
    ...row,
    id: matchId,
    home_score: row.home_score ?? row.home_goals,
    away_score: row.away_score ?? row.away_goals,
  } as Match
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useMatch(id?: string) {
  const numId = Number(id)
  const valid = Number.isFinite(numId) && numId > 0
  return useQuery<Match | null>({
    queryKey: ['match', id],
    enabled: valid,
    queryFn: async ({ signal }) => {
      if (!valid) return null
      const r = await fetch(`${ENDPOINTS.gateway}/api/matches/${numId}`, { signal })
      if (r.status === 404) return null
      if (!r.ok) {
        const body = await r.json().catch(() => ({}))
        const detail = typeof body?.detail === 'string' ? body.detail : body?.detail?.message
        throw new Error(detail || `Unable to load match (HTTP ${r.status})`)
      }
      return normalizeMatch(await r.json())
    },
    retry: false,
    staleTime: 10_000,
  })
}

// ── Probability bar ───────────────────────────────────────────────────────────

function ProbBar({ label, prob, color, recommended }: { label: string; prob?: number; color: string; recommended?: boolean }) {
  const pct = prob != null ? Math.round(prob * 100) : null
  return (
    <div className={cn(
      'flex-1 p-4 rounded-2xl text-center relative overflow-hidden transition-all',
      recommended
        ? 'bg-vit-500/12 border border-vit-500/40 shadow-lg shadow-vit-500/10'
        : 'bg-white/3 border border-white/6'
    )}>
      {recommended && (
        <span className="absolute top-2 right-2 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-vit-500 text-black">
          AI Pick
        </span>
      )}
      <p className="text-xs font-medium text-white/40 mb-1">{label}</p>
      <p className={cn('text-3xl font-bold font-mono tracking-tight', color)}>
        {pct != null ? `${pct}%` : '—'}
      </p>
    </div>
  )
}

// ── Secondary Markets Panel ───────────────────────────────────────────────────

function SecondaryMarketsPanel({ match }: { match: Match }) {
  const over25 = match.over_25_prob != null ? Math.round(match.over_25_prob * 100) : null
  const under25 = match.under_25_prob != null ? Math.round(match.under_25_prob * 100) : null
  const btts = match.btts_prob != null ? Math.round(match.btts_prob * 100) : null
  const noBtts = match.no_btts_prob != null ? Math.round(match.no_btts_prob * 100) : null
  const dnbHome = match.dnb_home_prob != null ? Math.round(match.dnb_home_prob * 100) : null
  const dnbAway = match.dnb_away_prob != null ? Math.round(match.dnb_away_prob * 100) : null

  if (over25 == null && under25 == null && btts == null && noBtts == null && dnbHome == null && dnbAway == null) return null

  return (
    <div className="bg-surface-800/50 border border-white/8 rounded-2xl p-6">
      <div className="flex items-center gap-2 mb-5">
        <Flame className="w-4 h-4 text-amber-400" />
        <h2 className="font-semibold text-white">Secondary Markets Forecast</h2>
      </div>

      <div className="grid sm:grid-cols-3 gap-4">
        {(over25 != null || under25 != null) && (
          <div className="p-4 rounded-xl bg-white/3 border border-white/6 text-center">
            <p className="text-xs text-white/40 mb-1">Over 2.5 Goals</p>
            <p className="text-2xl font-bold text-amber-400 font-mono">{over25 != null ? `${over25}%` : '—'}</p>
            <p className="text-[10px] text-white/30 mt-1">Under 2.5: {under25 != null ? `${under25}%` : '—'}</p>
          </div>
        )}

        {(btts != null || noBtts != null) && (
          <div className="p-4 rounded-xl bg-white/3 border border-white/6 text-center">
            <p className="text-xs text-white/40 mb-1">Both Teams To Score (BTTS)</p>
            <p className="text-2xl font-bold text-vit-400 font-mono">{btts != null ? `${btts}%` : '—'}</p>
            <p className="text-[10px] text-white/30 mt-1">No BTTS: {noBtts != null ? `${noBtts}%` : '—'}</p>
          </div>
        )}

        {(dnbHome != null || dnbAway != null) && (
          <div className="p-4 rounded-xl bg-white/3 border border-white/6 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <p className="text-xs text-white/40">Draw No Bet (DNB Home)</p>
            </div>
            <p className="text-2xl font-bold text-emerald-400 font-mono">{dnbHome != null ? `${dnbHome}%` : '—'}</p>
            <p className="text-[10px] text-white/30 mt-1">DNB Away: {dnbAway != null ? `${dnbAway}%` : '—'} (Draw Excluded)</p>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Tactical AI Insights Panel ────────────────────────────────────────────────

function TacticalPanel({ tactical }: { tactical: NonNullable<NonNullable<Match['intelligence']>['tactical']> }) {
  if (!tactical.summary && !tactical.recommendation && (!tactical.key_factors || tactical.key_factors.length === 0)) {
    return null
  }

  return (
    <div className="bg-gradient-to-br from-vit-600/10 via-surface-800/60 to-surface-800/80 border border-vit-500/25 rounded-2xl p-6 shadow-xl">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-lg bg-vit-500/20 border border-vit-500/30 flex items-center justify-center shrink-0">
          <Brain className="w-4 h-4 text-vit-400" />
        </div>
        <div>
          <h2 className="font-bold text-white text-base">Tactical AI Analysis</h2>
          <p className="text-xs text-vit-300/60">Grounded in Live Model & Team Form Features</p>
        </div>
      </div>

      {tactical.recommendation && (
        <div className="mb-4 p-3.5 rounded-xl bg-vit-500/15 border border-vit-500/30 flex items-start gap-3">
          <Zap className="w-4 h-4 text-vit-400 shrink-0 mt-0.5" />
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-vit-300 block mb-0.5">Recommendation</span>
            <p className="text-sm font-semibold text-white">{tactical.recommendation}</p>
          </div>
        </div>
      )}

      {tactical.summary && (
        <p className="text-sm text-white/80 leading-relaxed mb-4">
          {tactical.summary}
        </p>
      )}

      {tactical.key_factors && tactical.key_factors.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2.5">Key Factors</h3>
          <ul className="space-y-2">
            {tactical.key_factors.map((factor, idx) => (
              <li key={idx} className="flex items-start gap-2.5 text-xs text-white/70 bg-white/3 p-2.5 rounded-lg border border-white/5">
                <CheckCircle2 className="w-3.5 h-3.5 text-vit-400 shrink-0 mt-0.5" />
                <span>{factor}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ── Model breakdown row ───────────────────────────────────────────────────────

function ModelRow({ pred, i }: { pred: Prediction; i: number }) {
  const sideColor = pred.bet_side === 'home' ? 'text-vit-400' : pred.bet_side === 'away' ? 'text-amber-400' : 'text-white/50'
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: i * 0.06 }}
      className="flex items-center gap-4 p-4 rounded-xl bg-white/3 border border-white/6 hover:bg-white/5 transition-colors"
    >
      <div className="flex-1">
        <p className="text-sm font-medium text-white">{pred.model_name}</p>
        {pred.reasoning && <p className="text-xs text-white/35 mt-0.5 line-clamp-1">{pred.reasoning}</p>}
      </div>

      <span className={cn('px-2.5 py-1 rounded-lg text-xs font-semibold uppercase', sideColor, 'bg-white/5')}>
        {pred.bet_side}
      </span>

      <div className="text-right shrink-0">
        <p className="text-sm font-bold text-white font-mono">{Math.round(pred.confidence * 100)}%</p>
        <p className="text-[10px] text-white/30">confidence</p>
      </div>

      {pred.final_ev != null && (
        <div className="text-right shrink-0">
          <p className={cn('text-sm font-bold font-mono', pred.final_ev > 0 ? 'text-emerald-400' : 'text-red-400')}>
            {pred.final_ev > 0 ? '+' : ''}{pred.final_ev.toFixed(2)}
          </p>
          <p className="text-[10px] text-white/30">EV</p>
        </div>
      )}

      {pred.entry_odds != null && (
        <div className="text-right shrink-0 hidden sm:block">
          <p className="text-sm font-mono text-white/70">{pred.entry_odds.toFixed(2)}</p>
          <p className="text-[10px] text-white/30">odds</p>
        </div>
      )}
    </motion.div>
  )
}

// ── Consensus panel ───────────────────────────────────────────────────────────

type MatchConsensus = NonNullable<NonNullable<Match['intelligence']>['consensus']>

function ConsensusPanel({ consensus }: { consensus: MatchConsensus }) {
  const cards = [
    { label: 'Home Prob', prob: consensus.home_prob, color: 'text-vit-400' },
    { label: 'Draw Prob', prob: consensus.draw_prob, color: 'text-white/50' },
    { label: 'Away Prob', prob: consensus.away_prob, color: 'text-amber-400' },
  ]
  return (
    <div className="bg-surface-800/50 border border-white/8 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-5 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-vit-400" />
          <h2 className="font-semibold text-white">Model Consensus & Risk Metrics</h2>
        </div>
        {consensus.models_active != null && consensus.models_active > 0 && (
          <span className="px-2.5 py-1 rounded-full bg-vit-500/15 border border-vit-500/30 text-vit-300 text-xs font-medium">
            {consensus.models_active} active models
          </span>
        )}
      </div>

      <div className="flex gap-3 mb-4">
        {cards.map(c => (
          <div key={c.label} className="flex-1 p-3.5 rounded-xl text-center bg-white/3 border border-white/5">
            <p className="text-xs text-white/35 mb-1">{c.label}</p>
            <p className={cn('text-2xl font-bold font-mono', c.color)}>{c.prob != null ? `${Math.round(c.prob * 100)}%` : '—'}</p>
          </div>
        ))}
      </div>

      {(consensus.risk_score != null || consensus.model_agreement != null || consensus.elo_diff != null) && (
        <div className="grid grid-cols-3 gap-3 pt-4 border-t border-white/6 text-center text-xs">
          <div>
            <p className="text-white/35 mb-0.5">Risk Score</p>
            <p className="font-semibold text-white">{consensus.risk_score != null ? `${(consensus.risk_score * 100).toFixed(0)}/100` : 'Low'}</p>
          </div>
          <div>
            <p className="text-white/35 mb-0.5">Model Agreement</p>
            <p className="font-semibold text-emerald-400">{consensus.model_agreement != null ? `${Math.round(consensus.model_agreement * 100)}%` : 'High'}</p>
          </div>
          <div>
            <p className="text-white/35 mb-0.5">Elo Diff</p>
            <p className="font-semibold text-amber-400">{consensus.elo_diff != null ? `${consensus.elo_diff > 0 ? '+' : ''}${Math.round(consensus.elo_diff)}` : '—'}</p>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function MatchDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: match, isLoading: matchLoading, isError: matchIsError, error: matchError, refetch } = useMatch(id!)

  const [isProcessing, setIsProcessing] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [actionStatus, setActionStatus] = useState<'initializing' | 'failed' | null>(null)

  const steps = [
    'Collecting match statistical features & team form...',
    'Querying live market odds and bookmaker consensus...',
    'Executing 13-model AI ensemble (LSTM, XGBoost, Transformers)...',
    'Calculating vig-free edge & Kelly staking strategy...',
    'Recording provenance & on-chain verification snapshot...'
  ]

  const handleAction = async (endpoint: 'initialize' | 'rerun') => {
    if (!match) return
    setIsProcessing(true)
    setActionStatus('initializing')
    setErrorMessage(null)
    setStepIndex(0)

    const interval = setInterval(() => {
      setStepIndex(prev => (prev < steps.length - 1 ? prev + 1 : prev))
    }, 1200)

    try {
      const res = await fetch(`${ENDPOINTS.gateway}/api/matches/${match.id}/predict/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      clearInterval(interval)

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: 'Failed to process prediction' }))
        const detail = typeof errData?.detail === 'string' ? errData.detail : errData?.detail?.message
        throw new Error(detail || 'Failed to process prediction request')
      }

      await refetch()
      setActionStatus(null)
    } catch (err: unknown) {
      clearInterval(interval)
      const msg = err instanceof Error ? err.message : 'Prediction initialization failed'
      setErrorMessage(msg)
      setActionStatus('failed')
    } finally {
      setIsProcessing(false)
    }
  }

  if (matchLoading) {
    return (
      <div className="pt-24 min-h-screen flex items-center justify-center">
        <Spinner className="w-8 h-8" />
      </div>
    )
  }

  if (!match) {
    return (
      <div className="pt-24 min-h-screen flex flex-col items-center justify-center gap-4">
        <AlertCircle className="w-12 h-12 text-red-400" />
        <p className="text-white font-semibold">{matchIsError ? 'Unable to load match' : 'Match not found'}</p>
        {matchIsError && <p className="text-white/40 text-sm max-w-sm text-center">{(matchError as Error)?.message}</p>}
        <button onClick={() => navigate('/matches')} className="px-5 py-2 rounded-lg bg-vit-600 text-white text-sm">
          Back to Matches
        </button>
      </div>
    )
  }

  const status = actionStatus || match.prediction_status || 'not_initialized'
  const isLive = match.status?.toLowerCase() === 'live' || match.status?.toLowerCase() === 'in_play'
  const aiPick = match.intelligence?.attribution?.[0]?.bet_side
  const consensus = match.intelligence?.consensus
  const predictions = match.intelligence?.attribution ?? []
  const tactical = match.intelligence?.tactical

  return (
    <div className="pt-20 pb-20 min-h-screen relative">
      <div className="absolute inset-0 section-grid opacity-20 pointer-events-none" />

      <div className="relative max-w-4xl mx-auto px-4 sm:px-6">
        {/* Back nav */}
        <Link
          to="/matches"
          className="inline-flex items-center gap-1.5 text-sm text-white/40 hover:text-white/70 transition-colors mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Matches
        </Link>

        {/* Match Hero Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-800/70 border border-white/10 rounded-2xl p-8 mb-5 relative overflow-hidden"
        >
          {isLive && <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-emerald-500 to-emerald-400" />}

          {/* Meta header */}
          <div className="flex items-center justify-between mb-6 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-white/40">{match.league}</span>
              {match.sport && <span className="px-2 py-0.5 rounded text-[10px] bg-white/5 text-white/35 capitalize">{match.sport}</span>}
              <span className={cn(
                'px-2 py-0.5 rounded text-[10px] font-semibold uppercase',
                match.data_status === 'LIVE' ? 'bg-emerald-500/15 text-emerald-300' :
                match.data_status === 'CACHED' ? 'bg-sky-500/15 text-sky-300' :
                match.data_status === 'DEGRADED' ? 'bg-amber-500/15 text-amber-300' :
                'bg-white/8 text-white/35',
              )}>
                {match.data_status || 'UNAVAILABLE'}
              </span>
              {isLive && (
                <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />LIVE
                </span>
              )}
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 text-xs text-white/35">
                <Calendar className="w-3.5 h-3.5" />
                {new Date(match.kickoff_time).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
              </div>
            </div>
          </div>

          {/* Teams */}
          <div className="flex items-center justify-between gap-6 mb-8">
            <div className="flex-1 text-center">
              <p className="text-xl font-bold text-white">{match.home_team}</p>
              <p className="text-xs text-white/35 mt-1">Home</p>
            </div>

            <div className="text-center shrink-0">
              {match.home_score != null && match.away_score != null ? (
                <div className="flex items-center gap-4">
                  <span className="text-4xl font-bold text-white">{match.home_score}</span>
                  <span className="text-2xl text-white/30">:</span>
                  <span className="text-4xl font-bold text-white">{match.away_score}</span>
                </div>
              ) : (
                <span className="text-white/30 text-lg font-medium">vs</span>
              )}
              {match.status && <StatusBadge status={match.status} size="sm" />}
            </div>

            <div className="flex-1 text-center">
              <p className="text-xl font-bold text-white">{match.away_team}</p>
              <p className="text-xs text-white/35 mt-1">Away</p>
            </div>
          </div>

          {/* Venue / Meta info */}
          {(match.venue || match.referee) && (
            <div className="flex flex-wrap gap-4 pt-4 border-t border-white/6 text-xs text-white/35">
              {match.venue && <span>🏟 {match.venue}</span>}
              {match.referee && <span>👤 Referee: {match.referee}</span>}
              {match.attendance != null && <span>👥 {match.attendance.toLocaleString()} attendance</span>}
            </div>
          )}
        </motion.div>

        {/* --- PREDICTION STATE MACHINE CONTAINER --- */}
        <div className="mb-6">
          {/* STATE 1: NOT_INITIALIZED */}
          {status === 'not_initialized' && !isProcessing && (
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-surface-800/80 border border-vit-500/30 rounded-2xl p-8 text-center shadow-2xl relative overflow-hidden"
            >
              <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-vit-500/15 border border-vit-500/30 flex items-center justify-center text-vit-400">
                <Brain className="w-7 h-7 animate-pulse" />
              </div>
              <h2 className="text-xl font-bold text-white mb-2">AI Prediction Not Initialized</h2>
              <p className="text-sm text-white/60 max-w-md mx-auto mb-6">
                No active prediction exists for this match. Click below to generate real-time 13-model ensemble outputs, market edge metrics, and tactical analysis.
              </p>
              <button
                onClick={() => handleAction('initialize')}
                className="px-6 py-3.5 rounded-xl bg-vit-500 hover:bg-vit-400 text-black font-bold text-sm inline-flex items-center gap-2 shadow-lg shadow-vit-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <Play className="w-4 h-4 fill-black" />
                Initialize Prediction
              </button>
            </motion.div>
          )}

          {/* STATE 2: INITIALIZING or LOCAL PROCESSING */}
          {(status === 'initializing' || isProcessing) && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-surface-800/80 border border-vit-500/40 rounded-2xl p-8 shadow-2xl"
            >
              <div className="flex items-center gap-3 mb-6">
                <Spinner className="w-5 h-5 text-vit-400" />
                <div>
                  <h3 className="text-base font-bold text-white">Initializing AI Prediction Pipeline</h3>
                  <p className="text-xs text-vit-300/60">Executing multi-model ensemble intelligence</p>
                </div>
              </div>

              <div className="space-y-3">
                {steps.map((st, idx) => (
                  <div
                    key={st}
                    className={cn(
                      'flex items-center gap-3 text-xs p-3 rounded-xl border transition-all',
                      idx < stepIndex
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                        : idx === stepIndex
                        ? 'bg-vit-500/15 border-vit-500/40 text-white font-medium animate-pulse'
                        : 'bg-white/2 border-white/5 text-white/30'
                    )}
                  >
                    {idx < stepIndex ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : idx === stepIndex ? (
                      <Spinner className="w-3.5 h-3.5 text-vit-400 shrink-0" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-white/20 shrink-0" />
                    )}
                    <span>{st}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* STATE 3: FAILED */}
          {status === 'failed' && !isProcessing && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-red-500/10 border border-red-500/30 rounded-2xl p-6 text-center"
            >
              <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
              <h3 className="text-base font-bold text-white mb-1">Prediction Generation Failed</h3>
              <p className="text-xs text-red-300/80 mb-4 max-w-md mx-auto">
                {match.error_message || errorMessage || 'An unexpected error occurred during prediction generation.'}
              </p>
              <button
                onClick={() => handleAction('initialize')}
                className="px-5 py-2.5 rounded-xl bg-red-500/20 hover:bg-red-500/30 text-red-300 font-semibold text-xs border border-red-500/40 inline-flex items-center gap-2"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Retry Prediction
              </button>
            </motion.div>
          )}

          {/* STATE 4: STALE WARNING */}
          {status === 'stale' && !isProcessing && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 mb-4 flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-2.5">
                <Clock className="w-5 h-5 text-amber-400 shrink-0" />
                <div>
                  <p className="text-xs font-bold text-amber-300 uppercase tracking-wider">Stale Prediction</p>
                  <p className="text-xs text-white/70">
                    Last calculated: {match.provenance?.generated_at ? new Date(match.provenance.generated_at).toLocaleString() : 'Over 24h ago'}
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleAction('rerun')}
                className="px-4 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 font-bold text-xs border border-amber-500/40 inline-flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Refresh Prediction
              </button>
            </div>
          )}

          {/* STATE 5: READY (or STALE with existing prediction) */}
          {(status === 'ready' || status === 'stale') && !isProcessing && (
            <>
              {/* Provenance Header Bar */}
              <div className="bg-surface-800/60 border border-white/8 rounded-2xl p-4 mb-5 flex items-center justify-between flex-wrap gap-3 text-xs">
                <div className="flex items-center gap-2.5">
                  {match.is_seed ? (
                    <span className="px-2.5 py-1 rounded-md bg-amber-500/15 border border-amber-500/30 text-amber-300 font-bold flex items-center gap-1.5">
                      <Database className="w-3.5 h-3.5" /> Demo / Seeded Data
                    </span>
                  ) : (
                    <span className="px-2.5 py-1 rounded-md bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-bold flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5" /> Live AI Prediction
                    </span>
                  )}
                  {match.provenance?.source && (
                    <span className="text-white/40">Data: {match.provenance.source}</span>
                  )}
                  {match.provenance?.job_id && (
                    <span className="text-white/40 font-mono hidden sm:inline">Job: {match.provenance.job_id}</span>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {match.provenance?.model_version && (
                    <span className="text-white/40">Model: {match.provenance.model_version}</span>
                  )}
                  <button
                    onClick={() => handleAction('rerun')}
                    className="px-3 py-1.5 rounded-lg bg-vit-500/15 hover:bg-vit-500/25 border border-vit-500/30 text-vit-300 font-semibold text-xs inline-flex items-center gap-1.5 transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Re-run Prediction
                  </button>
                </div>
              </div>

              {/* Primary Probability Distribution Bars */}
              <div className="flex gap-3 mb-5">
                <ProbBar label="Home Win" prob={match.home_prob} color="text-vit-400" recommended={aiPick === 'home'} />
                <ProbBar label="Draw" prob={match.draw_prob} color="text-white/50" recommended={aiPick === 'draw'} />
                <ProbBar label="Away Win" prob={match.away_prob} color="text-amber-400" recommended={aiPick === 'away'} />
              </div>

              {/* Key Metrics Summary */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
                <div className="bg-surface-800/50 border border-white/8 rounded-xl p-4 text-center">
                  <Brain className="w-4 h-4 mx-auto mb-2 text-vit-400" />
                  <p className="text-xl font-bold text-vit-400 font-mono">{aiPick ? aiPick.toUpperCase() : 'N/A'}</p>
                  <p className="text-xs text-white/35 mt-0.5">AI Pick</p>
                </div>

                <div className="bg-surface-800/50 border border-white/8 rounded-xl p-4 text-center">
                  <Target className="w-4 h-4 mx-auto mb-2 text-emerald-400" />
                  <p className="text-xl font-bold text-emerald-400 font-mono">
                    {match.confidence != null ? `${Math.round(match.confidence * 100)}%` : '—'}
                  </p>
                  <p className="text-xs text-white/35 mt-0.5">Model Confidence</p>
                </div>

                <div className="bg-surface-800/50 border border-white/8 rounded-xl p-4 text-center">
                  <TrendingUp className="w-4 h-4 mx-auto mb-2 text-emerald-400" />
                  <p className="text-xl font-bold text-emerald-400 font-mono">
                    {match.edge != null ? `${match.edge > 0 ? '+' : ''}${match.edge.toFixed(3)}` : '—'}
                  </p>
                  <p className="text-xs text-white/35 mt-0.5">Vig-Free Edge</p>
                </div>

                <div className="bg-surface-800/50 border border-white/8 rounded-xl p-4 text-center">
                  <Activity className="w-4 h-4 mx-auto mb-2 text-amber-400" />
                  <p className="text-xl font-bold text-amber-400 font-mono">
                    {match.odds?.home ? match.odds.home.toFixed(2) : '—'}
                  </p>
                  <p className="text-xs text-white/35 mt-0.5">Home Market Odds</p>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Tactical AI Analysis */}
        {(status === 'ready' || status === 'stale') && tactical && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="mb-5">
            <TacticalPanel tactical={tactical} />
          </motion.div>
        )}

        {/* Secondary Markets */}
        {(status === 'ready' || status === 'stale') && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mb-5">
            <SecondaryMarketsPanel match={match} />
          </motion.div>
        )}

        {/* Consensus */}
        {(status === 'ready' || status === 'stale') && consensus && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }} className="mb-5">
            <ConsensusPanel consensus={consensus} />
          </motion.div>
        )}

        {/* Model breakdown */}
        {(status === 'ready' || status === 'stale') && predictions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="bg-surface-800/50 border border-white/8 rounded-2xl p-6"
          >
            <div className="flex items-center gap-2 mb-5">
              <BarChart3 className="w-4 h-4 text-vit-400" />
              <h2 className="font-semibold text-white">Model Breakdown</h2>
              <span className="ml-auto text-xs text-white/30">{predictions.length} models</span>
            </div>
            <div className="space-y-2.5">
              {predictions.map((p, i) => <ModelRow key={`${p.model_name}-${i}`} pred={p} i={i} />)}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
