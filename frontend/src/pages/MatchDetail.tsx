import { useParams, useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft, Trophy, Calendar, Target, TrendingUp, TrendingDown,
  Brain, BarChart3, Users, Zap, AlertCircle, Activity,
  CheckCircle2, Clock, Minus,
} from 'lucide-react'
import { cn, timeAgo } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Match {
  id: number
  match_id?: number
  home_team: string
  away_team: string
  league: string
  sport?: string
  kickoff_time: string
  status?: string
  home_score?: number
  away_score?: number
  home_prob?: number
  draw_prob?: number
  away_prob?: number
  venue?: string
  referee?: string
  attendance?: number
  confidence?: number
  edge?: number
  odds?: { home?: number; draw?: number; away?: number }
  intelligence?: {
    consensus?: {
      home_prob?: number
      draw_prob?: number
      away_prob?: number
      confidence?: number
    }
    attribution?: Prediction[]
  }
}

interface Prediction {
  model_name: string
  bet_side: 'home' | 'draw' | 'away'
  confidence: number
  final_ev?: number
  entry_odds?: number
  reasoning?: string
  accuracy_overall?: number
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useMatch(id: string) {
  return useQuery<Match | null>({
    queryKey: ['match', id],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/matches/${id}`, { signal })
      return r.ok ? r.json() : null
    },
    retry: false,
    staleTime: 30_000,
  })
}

// ── Probability bar ───────────────────────────────────────────────────────────

function ProbBar({ label, prob, color, recommended }: { label: string; prob?: number; color: string; recommended?: boolean }) {
  const pct = prob != null ? Math.round(prob * 100) : null
  return (
    <div className={cn('flex-1 p-4 rounded-xl text-center', recommended ? 'bg-vit-500/10 border border-vit-500/30' : 'bg-white/3')}>
      <p className="text-xs text-white/40 uppercase tracking-wider mb-2">{label}</p>
      <p className={cn('text-3xl font-bold mb-2', color)}>{pct != null ? `${pct}%` : '—'}</p>
      <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct ?? 0}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className={cn('h-full rounded-full', color.replace('text-', 'bg-'))}
        />
      </div>
      {recommended && <p className="text-[10px] text-vit-400 mt-2 font-medium">AI PICK</p>}
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
        <p className="text-sm font-bold text-white">{Math.round(pred.confidence * 100)}%</p>
        <p className="text-[10px] text-white/30">confidence</p>
      </div>

      {pred.final_ev != null && (
        <div className="text-right shrink-0">
          <p className={cn('text-sm font-bold', pred.final_ev > 0 ? 'text-emerald-400' : 'text-red-400')}>
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
    { label: 'Home',  prob: consensus.home_prob, color: 'text-vit-400' },
    { label: 'Draw',  prob: consensus.draw_prob, color: 'text-white/50' },
    { label: 'Away',  prob: consensus.away_prob, color: 'text-amber-400' },
  ]
  return (
    <div className="bg-surface-800/50 border border-white/8 rounded-2xl p-6">
      <div className="flex items-center gap-2 mb-5">
        <Users className="w-4 h-4 text-vit-400" />
        <h2 className="font-semibold text-white">Model Consensus</h2>
      </div>
      <div className="flex gap-3">
        {[
          ...cards,
        ].map(c => (
          <div key={c.label} className="flex-1 p-3 rounded-xl text-center bg-white/3">
            <p className="text-xs text-white/35 mb-1">{c.label}</p>
            <p className={cn('text-xl font-bold', c.color)}>{c.prob != null ? `${Math.round(c.prob * 100)}%` : '—'}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function MatchDetail() {
  const { id }  = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: match, isLoading: matchLoading } = useMatch(id!)

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
        <p className="text-white font-semibold">Match not found</p>
        <button onClick={() => navigate('/matches')} className="px-5 py-2 rounded-lg bg-vit-600 text-white text-sm">
          Back to Matches
        </button>
      </div>
    )
  }

  const isLive = match.status?.toLowerCase() === 'live' || match.status?.toLowerCase() === 'in_play'
  const aiPick = match.intelligence?.attribution?.[0]?.bet_side
  const consensus = match.intelligence?.consensus
  const predictions = match.intelligence?.attribution ?? []

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

        {/* Match hero */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-800/70 border border-white/10 rounded-2xl p-8 mb-5 relative overflow-hidden"
        >
          {isLive && <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-emerald-500 to-emerald-400" />}

          {/* Meta */}
          <div className="flex items-center justify-between mb-6 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-white/40">{match.league}</span>
              {match.sport && <span className="px-2 py-0.5 rounded text-[10px] bg-white/5 text-white/35 capitalize">{match.sport}</span>}
              {isLive && (
                <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />LIVE
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-white/35">
              <Calendar className="w-3.5 h-3.5" />
              {new Date(match.kickoff_time).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
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

          {/* Probability bars */}
          <div className="flex gap-3">
            <ProbBar label="Home" prob={match.home_prob} color="text-vit-400"  recommended={aiPick === 'home'} />
            <ProbBar label="Draw" prob={match.draw_prob} color="text-white/50" recommended={aiPick === 'draw'} />
            <ProbBar label="Away" prob={match.away_prob} color="text-amber-400" recommended={aiPick === 'away'} />
          </div>

          {/* Venue / meta */}
          {(match.venue || match.referee) && (
            <div className="flex flex-wrap gap-4 mt-5 pt-5 border-t border-white/6 text-xs text-white/35">
              {match.venue    && <span>🏟 {match.venue}</span>}
              {match.referee  && <span>👤 Referee: {match.referee}</span>}
              {match.attendance != null && <span>👥 {match.attendance.toLocaleString()} attendance</span>}
            </div>
          )}
        </motion.div>

        {/* AI summary */}
        {(match.confidence != null || match.edge != null) && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5"
          >
            {[
              { label: 'AI Pick',     value: aiPick?.toUpperCase() ?? '—',           icon: Brain,       color: 'text-vit-400'     },
              { label: 'Confidence',  value: match.confidence != null ? `${Math.round(match.confidence * 100)}%` : '—', icon: Target, color: 'text-emerald-400' },
              { label: 'Market Edge', value: match.edge != null ? `${match.edge > 0 ? '+' : ''}${match.edge.toFixed(3)}` : '—', icon: TrendingUp, color: match.edge != null && match.edge > 0 ? 'text-emerald-400' : 'text-red-400' },
              { label: 'Home Odds',  value: match.odds?.home?.toFixed(2) ?? '—',            icon: Activity,    color: 'text-amber-400'   },
            ].map(s => (
              <div key={s.label} className="bg-surface-800/50 border border-white/8 rounded-xl p-4 text-center">
                <s.icon className={cn('w-4 h-4 mx-auto mb-2', s.color)} />
                <p className={cn('text-xl font-bold', s.color)}>{s.value}</p>
                <p className="text-xs text-white/35 mt-0.5">{s.label}</p>
              </div>
            ))}
          </motion.div>
        )}

        {/* Consensus */}
        {consensus && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mb-5">
            <ConsensusPanel consensus={consensus} />
          </motion.div>
        )}

        {/* Model breakdown */}
        {predictions.length > 0 && (
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

        {!predictions.length && (
          <div className="flex items-center gap-2.5 p-4 rounded-xl bg-white/3 border border-white/8 text-sm text-white/40">
            <AlertCircle className="w-4 h-4 shrink-0" />
            AI predictions are not available for this match yet.
          </div>
        )}
      </div>
    </div>
  )
}
